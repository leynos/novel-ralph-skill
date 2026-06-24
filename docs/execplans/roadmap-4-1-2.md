# Implement the `novel-compile --check` read-only divergence checker

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DRAFT (revision 3 — design-review round 3)

## Purpose / big picture

`novel-compile` already regenerates `working/manuscript/compiled.md`
deterministically as a **mutator** (roadmap task 4.1.1, delivered). This task
adds the read-only half the design names in `docs/novel-ralph-harness-design.md`
§4.3: a `--check` flag that makes `novel-compile` a **checker** which reports
whether `compiled.md` is the ordered concatenation of the present chapter
drafts, **writes nothing**, and exits `4` (an actionable finding) when the
compile is stale or absent so the agent knows to regenerate. It is the
command-line surface of the same comparison the `novel-done` `compile_consistent`
clause makes, so the two cannot disagree about whether `compiled.md` is current.

After this change a user can run, from a project's process directory:

```console
$ novel-compile --check        # compiled.md matches the drafts
{"command": "novel-compile", "schema_version": 1, "ok": true,
 "working_dir": "working",
 "result": {"checked": "working/manuscript/compiled.md",
            "chapters": 3, "diverged": false},
 "messages": ["working/manuscript/compiled.md matches the chapter drafts"]}
$ echo $?
0
```

```console
$ novel-compile --check        # compiled.md is stale or absent
{"command": "novel-compile", "schema_version": 1, "ok": false,
 "working_dir": "working",
 "result": {"checked": "working/manuscript/compiled.md",
            "chapters": 3, "diverged": true},
 "messages": ["working/manuscript/compiled.md diverges from the chapter drafts; \
regenerate it with novel-compile"]}
$ echo $?
4
```

The plain `novel-compile` (no flag) write path is unchanged: it still
regenerates `compiled.md` and exits `0`. `--check` writes nothing on any path.
The behaviour is observed through four independent proofs, each delivered by a
named work item below:

1. a new behavioural scenario set in `tests/features/compile.feature` (Work
   item 3);
2. a machine-mode envelope snapshot of the `--check` envelopes (Work item 4);
3. an end-to-end entry-point test driving the real console-script body
   `stub.novel_compile()` with `sys.argv = ["novel-compile", "--check"]` (Work
   item 5), which is the only layer that exercises `parse_global_flags` + `_drive`
   forwarding `--check` to `run`;
4. an agreement property pinning `--check` against the `compile_consistent`
   clause over the corpus (Work item 4).

See "Validation and acceptance".

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **`--check` is a read-only checker: it writes nothing on any path.** Design
  §3.3 places `novel-compile --check` in the checker column; ADR-001 forbids a
  checker touching disk. The `--check` body must never call
  `write_text_atomically`, never open a `[pending_turn]` bracket, and never
  create `compiled.md`. It may only *read* `state.toml` and the manuscript tree.
  (`docs/adr-001-deterministic-judgemental-boundary.md`; design §3.3 table.)
- **`--check` and the `novel-done` `compile_consistent` clause share one
  comparison routine.** Both must read the verdict from the single production
  site `novel_ralph_skill.state.compile_model.compiled_matches_drafts(state,
  working_dir)`, which returns the three-valued
  `CompiledComparison` (`ABSENT` / `MATCHES` / `DIVERGES`). `--check` must not
  re-implement the concatenate-and-compare logic. This is the roadmap 4.1.2
  success criterion — "`novel-compile --check` and the `novel-done` compile
  clause agree on every corpus fixture because they share one routine" — and the
  developers-guide "one owner for compiled.md equals the ordered draft
  concatenation" rule. (`novel_ralph_skill/state/compile_model.py:57-111`;
  roadmap 3.1.3; `docs/developers-guide.md` lines 595-625.)
- **`--check` projects the verdict to the `compile_consistent` polarity: only
  `MATCHES` is satisfied.** Both `ABSENT` and `DIVERGES` are findings (exit `4`).
  This matches the `novel-done` `compile_consistent` clause, which holds **iff**
  the verdict is `MATCHES` (`novel_ralph_skill/state/done_predicate.py:221-271`):
  an absent `compiled.md` is "not current — regenerate it", exactly as a stale
  one is. This is the **opposite** polarity to the §5.4 `novel-state check`
  disk-evidence detector (`_check_compiled_matches_drafts`), which treats
  `ABSENT` as *vacuously satisfied* ("nothing to diverge from"); the two
  polarities are correct for their different jobs and are reconciled inside the
  one shared helper. The roadmap pins agreement with the **`novel-done` compile
  clause**, not the §5.4 detector, so the `MATCHES`-only projection is the
  required one (see Decision Log D-POLARITY). (Design §4.3 "exiting 4 when the
  compile is stale"; §4.2 lines 318-327; roadmap 4.1.2.)
- **The `--check` exit code is `4` (`ExitCode.ACTIONABLE_FINDING`), never `1`.**
  Design §3.2 reserves `1` for a *benign negative* the harness loops on without
  intervention, and `4` for an *actionable finding* the agent must adjudicate or
  repair. A stale or absent `compiled.md` is the latter: the harness regenerates
  it. The §3.2 table and §3.3 row both name `novel-compile --check` at exit `4`.
  Satisfied (`MATCHES`) is exit `0`. (`novel_ralph_skill/contract/exit_codes.py`;
  design §3.2.)
- **The fault boundary matches the write path and the done clause exactly.** A
  missing or unparseable `state.toml`, an absent working tree, an absent or empty
  `[chapters]` manifest, or an unreadable/undecodable `draft.md` or `compiled.md`
  is exit `3` (`StateInputError`), never the benign `1` and never the finding
  `4`. The `--check` body reuses `novel-state`'s boundary helpers
  (`_load_or_state_error`, `state_path`, `working_dir`, `STATE_INPUT_ERRORS`)
  exactly as the write path does. A *missing* `draft.md` contributes the empty
  string (benign) inside `compiled_matches_drafts`; a *missing* `compiled.md` is
  the `ABSENT` verdict (a finding, not a fault). (Design §3.2, §3.4;
  `novel_ralph_skill/commands/_compile.py:62-127`.)
- **The empty-manifest refusal is preserved under `--check`.** An absent or
  empty `[chapters]` manifest has no authoritative ordering, so `--check` refuses
  with exit `3` and the same message the write path uses, *before* any
  comparison. This keeps the two modes' state-error boundary identical. (Design
  §10 "Chapter manifest missing or non-bijective during compile";
  `novel_ralph_skill/commands/_compile.py:99-103`.)
- **`--check` is a kw-only boolean flag on the existing single default
  callback.** `novel-compile` maps 1:1 onto one operation with two modes, so it
  stays a single `@app.default` body taking `*, check: bool = False`, not a
  subcommand multiplexer (design §4.3; ADR-005). Verified against the locked
  cyclopts 4.18.0: a kw-only `check: bool = False` yields `--check`/`--no-check`,
  `--check` reaches the body and binds `True`, the no-arg path binds `False`, and
  an unknown positional still raises `UnusedCliTokensError` (a `CycloptsError`,
  routed to exit `2` by the shared runner). See Decision Log D-FLAG for the
  transcript. (`novel_ralph_skill/contract/runner.py:52-81, 223-250`.)
- **The four-flag contract and the shared `run` wrapper are unchanged.** The app
  is still built by `make_contract_app("novel-compile")`; the body still returns
  a `CommandOutcome`; the shared `run` wrapper still owns every `sys.exit` and
  envelope. No new exit-code translation is added — `run` already passes a body's
  `ExitCode.ACTIONABLE_FINDING` through unchanged.
  (`novel_ralph_skill/contract/runner.py:190-250`.)
- **British English, Oxford spelling.** All prose, docstrings, comments, and
  commit messages use en-GB Oxford spelling (`-ize`/`-yse`/`-our`), per
  `AGENTS.md` and the `en-gb-oxendict` convention.

## Tolerances (exception triggers)

Thresholds that trigger escalation when breached.

- **Scope:** if the implementation touches more than 8 files or ~250 net lines,
  stop and escalate. The expected footprint is `_compile.py`, the corpus
  exports (if a fixture must be added), `pyproject.toml` is *not* touched (the
  console script already routes through `stub.novel_compile`), the two guides,
  and the new/extended test modules.
- **Interface:** if the `compiled_matches_drafts` helper signature or the
  `CompiledComparison` enum must change to serve `--check`, stop and escalate —
  the shared routine is the load-bearing contract and a change to it ripples to
  the done clause and the §5.4 detector.
- **Dependencies:** if any work item appears to need a new external dependency
  (e.g. `hashlib`, a new cyclopts feature), stop and escalate; the verdict is a
  byte comparison over in-memory strings (D-BYTE-COMPARE) and needs none.
- **Polarity ambiguity:** if a corpus fixture surfaces a case where `--check`
  and the `compile_consistent` clause *cannot* be made to agree under the
  `MATCHES`-only projection, stop and escalate rather than special-casing.
- **Iterations:** if the gate (`make all`) still fails after 3 fix attempts on
  one work item, stop and escalate.

## Risks

- Risk: `--check` and the `compile_consistent` clause drift in polarity (e.g.
  `--check` treats `ABSENT` as satisfied like the §5.4 detector), so the roadmap
  agreement criterion is violated.
  Severity: high
  Likelihood: medium
  Mitigation: route both through `compiled_matches_drafts`, project with the
  identical `is CompiledComparison.MATCHES` test the clause uses, and pin
  agreement with a property test over the corpus (Work item 4, R-AGREE).

- Risk: a future reader assumes "compile-and-hash" means a digest is computed,
  re-introducing `hashlib`. The shipped shared routine is a direct byte
  comparison, not a digest (roadmap 3.1.2 D-BYTE-COMPARE).
  Severity: low
  Likelihood: medium
  Mitigation: Decision Log D-BYTE-COMPARE records this; the developers-guide
  "compile-and-hash" wording is corrected to "compile-and-compare" in Work
  item 5; no `hashlib` import is added.

- Risk: `--check` accidentally writes `compiled.md` (e.g. by reusing too much of
  the write body), breaking the read-only checker constraint and ADR-001.
  Severity: high
  Likelihood: low
  Mitigation: the `--check` branch shares only the *load + manifest-guard +
  verdict* prefix and never reaches `write_text_atomically`; a behavioural
  scenario and a unit test both assert no `compiled.md` is created/modified on
  the `--check` path (R-NOWRITE).

- Risk: the cyclopts flag binding changes the write path's behaviour (e.g. an
  unknown positional now routes to the body instead of erroring).
  Severity: medium
  Likelihood: low
  Mitigation: the flag is kw-only; verified that an unknown positional still
  raises `UnusedCliTokensError` under cyclopts 4.18.0 (D-FLAG). A usage-error
  test pins exit `2` for a stray positional.

- Risk: the in-process tests (Work items 2–4) all drive `run(build_app(),
  ["--check"], …)` directly and so never exercise `parse_global_flags` + `_drive`
  (`novel_ralph_skill/commands/stub.py:100-105`), the only layer that strips
  `--human` and forwards the residual argv (including `--check`) to `run`. A
  future change to `parse_global_flags`/`_drive` that mishandled `--check` (e.g.
  began consuming a second flag, or filtered `--check` out) would pass every
  in-process test yet break the real console-script path.
  Severity: high
  Likelihood: low
  Mitigation: Work item 5 adds two `--check` cases to `tests/test_compile_e2e.py`
  driving the real `stub.novel_compile()` body with `sys.argv =
  ["novel-compile", "--check"]` (coherent tree → exit `0`, `diverged: false`;
  stale tree → exit `4`, `diverged: true`), regression-pinning the entry-point
  forwarding (R-ENTRYPOINT). Verified today's behaviour: `parse_global_flags`
  filters only `_HUMAN_FLAG` and returns every other token in the residual argv
  (`novel_ralph_skill/contract/runner.py:109-111`), so `_drive` forwards
  `--check` to `run` unchanged.

## Progress

- [x] Work item 1 — Add the `--check` read-only verdict body and wire the flag.
  Delivered in commit `07da73d`. Factored the manifest guard into
  `_require_chapter_manifest` (shared by `compile_manuscript` and
  `check_compiled`), added `check_compiled`, and changed the default callback to
  `def _compile(*, check: bool = False)`. `make all` green; coderabbit clean.
  Note: Ruff's `implicit-string-concatenation-in-collection-literal` required
  wrapping the multi-line finding message in parentheses inside the `messages`
  list.
- [x] Work item 2 — Unit-test the `--check` verdict, fault boundary, and
  no-write guarantee. Delivered in commit `256024a` as
  `tests/test_compile_check_unit.py` (7 cases): the three verdicts, the
  empty-manifest / missing-state / undecodable-draft exit-`3` boundary, and the
  stray-positional exit-`2` pin, each driving `["--check"]` via a dedicated
  `_run_check`.
- [x] Work item 3 — Add the behavioural scenarios to `compile.feature`.
  Delivered in commit `1190967`: four scenarios in `compile.feature` plus new
  step definitions in `tests/steps/compile_steps.py` (the binder is untouched).
  The present/stale paths assert byte-for-byte unchanged via captured bytes; the
  absent path reuses the not-exists Then.
- [x] Work item 4 — Pin `--check` ⇔ `compile_consistent` agreement (property)
  and snapshot the `--check` envelopes. Delivered in commit `c3f8da4`:
  `tests/test_compile_check_agreement.py` is a parametrized table over four
  corpus specs spanning `MATCHES`/`DIVERGES`/`ABSENT` (Hypothesis not required
  for a closed enumeration); `tests/test_compile_check_snapshots.py` pins the
  two envelopes. Removed a brittle cross-check on `state_path()` (returns the
  relative `working/state.toml`, not the absolute path).
- [x] Work item 5 — Pin the entry-point path: add `--check` cases to
  `tests/test_compile_e2e.py` driving `stub.novel_compile()`. Delivered in
  commit `a7b18a5`: coherent → exit `0`/`diverged: false`; stale → exit
  `4`/`diverged: true`; each asserts `compiled.md` byte-for-byte unchanged.
- [x] Work item 6 — Update the developers' guide and users' guide; run the
  Markdown gates. Documented `--check` in both guides, corrected the
  "compile-and-hash" wording to a byte comparison, and noted the `MATCHES`-only
  polarity contrast with the §5.4 detector. `make markdownlint`, `make nixie`,
  and `make all` all green.

## Surprises & discoveries

- Observation: the roadmap calls the shared routine a "compile-and-hash"
  function, but the delivered shared routine (`compiled_matches_drafts`) is a
  **direct byte comparison**, not a digest.
  Evidence: `novel_ralph_skill/state/compile_model.py:108-111` compares
  `compiled.read_text(...) == expected`; `done_predicate.py:240-241` records
  "The helper performs a direct byte comparison, not a digest (ExecPlan
  D-BYTE-COMPARE): a boolean over two in-memory strings needs no `hashlib`."
  Impact: 4.1.2 reuses the byte-comparison helper; the "hash" wording in the
  roadmap and developers-guide is historical and is corrected in Work item 5. No
  `hashlib` is introduced.

- Observation: the corpus already exposes every fixture `--check` needs.
  Evidence: `tests/working_corpus/_specs.py` `WorkingTreeSpec.compiled` accepts
  `None` (no `compiled.md` → `ABSENT`), `COMPILED_AUTO` (the hash-equal coherent
  compile → `MATCHES`), or an arbitrary string (stale/contradictory →
  `DIVERGES`); `_done_predicate_specs.py` already builds
  `DONE_PREDICATE_ALL_HOLD` (matches), `DONE_PREDICATE_SOLE_STALE_COMPILE`
  (present-stale), and `dc.replace(..., compiled=None)` (absent).
  Impact: Work items 2–4 reuse these; no new corpus category is needed (a
  fixture is only added if an agreement-property scan needs one not already
  exported).

## Decision log

- Decision: `--check` projects the shared verdict with only `CompiledComparison.
  MATCHES` satisfied; both `ABSENT` and `DIVERGES` are exit-`4` findings.
  Rationale (D-POLARITY): roadmap 4.1.2 requires `--check` to *agree with the
  `novel-done` compile clause* on every corpus fixture, and that clause holds
  iff the verdict is `MATCHES` (`done_predicate.py:271`). Design §4.3 says
  `--check` exits 4 "when the compile is stale so the agent knows to regenerate";
  an *absent* `compiled.md` is equally "not current — regenerate", so it is a
  finding too. This is deliberately the *opposite* polarity to the §5.4
  `novel-state check` detector (absent = satisfied); the roadmap pins agreement
  with the done clause, not that detector. Pinned by the Work item 4 agreement
  property.
  Date/Author: 2026-06-24, planning agent.

- Decision: `--check` is a kw-only `check: bool = False` parameter on the single
  existing `@app.default` callback (D-FLAG).
  Rationale: `novel-compile` is one operation with two modes (design §4.3,
  ADR-005), so no subcommand multiplexer is warranted. Verified empirically
  against the locked cyclopts 4.18.0: `app(['--check'])` binds `True`,
  `app([])` binds `False`, `app(['--no-check'])` binds `False`, an unknown
  positional raises `UnusedCliTokensError`, and an unknown option raises
  `UnknownOptionError` — both `CycloptsError` subclasses the shared runner routes
  to exit `2`. The `parse_global_flags` pre-parse strips only `--human`, so it
  leaves `--check` in the residual argv untouched.
  Date/Author: 2026-06-24, planning agent.

- Decision: the verdict is computed by reusing `compiled_matches_drafts`; no
  digest, no `hashlib` (D-BYTE-COMPARE).
  Rationale: the shared production site already performs the byte comparison;
  introducing a hash would be a second comparison rule and re-open the drift the
  3.1.3 single-owner refactor closed.
  Date/Author: 2026-06-24, planning agent.

- Decision: the `--check` success `result` uses checker-shaped keys
  (`checked`, `chapters`, `diverged`) and carries no `compiled`/`bytes` write
  keys; it does **not** add a `violations` key.
  Rationale (D-RESULT): design §3.3 reserves `violations` for `novel-state
  check` alone; `novel-compile --check` is a divergence *flag*, not a violation
  enumerator (its finding is a single boolean), so the bounded `diverged`
  boolean is the machine-actionable datum, mirroring how the `compile_consistent`
  clause "reports only the boolean, never per-chapter hashes, so the payload
  stays bounded as the chapter count grows" (roadmap 3.1.2). The write path's
  `result` keys (`compiled`, `bytes`) name *what changed* and are wrong for a
  checker that changes nothing.
  Date/Author: 2026-06-24, planning agent.

- Decision: every `--check` test drives `run(build_app(), ["--check"], …)` with
  a distinct driver, never reusing the existing `[]`-argv write-path helpers
  (D-CHECK-ARGV).
  Rationale: the BDD helper `_run_compile` (`tests/steps/compile_steps.py`) and
  the snapshot helper `_drive` (`tests/test_compile_snapshots.py`) hardcode argv
  `[]`, which exercises the write path. A test copying them verbatim would write
  `compiled.md` and silently pass the no-write and verdict assertions for the
  wrong reason (false green). Each `--check` test therefore adds a dedicated
  `--check` runner passing `["--check"]`. Verified the flag binding under cyclopts
  4.18.0 in D-FLAG.
  Date/Author: 2026-06-24, planning agent.

- Decision: the present-but-stale no-write invariant uses a **new** Then that
  captures `compiled.md`'s bytes before the `--check` run and asserts they are
  unchanged after; only the absent/empty cases reuse the existing
  `asserts_no_compiled` not-exists Then (D-STALE-NOWRITE).
  Rationale: `asserts_no_compiled` asserts `not compiled.exists()`
  (`tests/steps/compile_steps.py`), which is false when `compiled.md` is present
  and stale. Reusing it on the stale path would assert the wrong invariant. The
  stale path needs "present file left byte-for-byte unchanged", a distinct step.
  Date/Author: 2026-06-24, planning agent.

- Decision: the four-proof Purpose includes a dedicated entry-point proof
  (D-ENTRYPOINT). Work item 5 adds `--check` cases to `tests/test_compile_e2e.py`
  driving the real console-script body `stub.novel_compile()` with `sys.argv =
  ["novel-compile", "--check"]`, mirroring the established
  `monkeypatch.setattr(sys, "argv", [_COMMAND])` pattern in that module.
  Rationale: the in-process `run(build_app(), ["--check"], …)` tests in Work
  items 2–4 bypass `parse_global_flags` + `_drive`
  (`novel_ralph_skill/commands/stub.py:100-105`), so without an entry-point case
  the Purpose's third proof has no work item and a regression in argv forwarding
  would go unpinned (round-3 blocking point). Verified `parse_global_flags`
  strips only `--human` (`runner.py:109-111`); the path forwards `--check` today.
  Date/Author: 2026-06-24, planning agent.

- Decision: new behavioural step definitions are added to
  `tests/steps/compile_steps.py`, and only new scenario text to
  `tests/features/compile.feature`; the binder `tests/test_compile_bdd.py` is not
  edited (D-STEP-FILE).
  Rationale: `test_compile_bdd.py` only binds (`scenarios(...)` plus
  `from steps.compile_steps import *`); pytest-bdd discovers steps from the
  star-imported namespace. Steps placed in the binder would be outside that
  namespace and the scenarios would not bind.
  Date/Author: 2026-06-24, planning agent.

## Outcomes & retrospective

Delivered. All six work items landed as atomic commits (`07da73d`, `256024a`,
`1190967`, `c3f8da4`, `a7b18a5`, `c242f77`); `make all`, `make markdownlint`,
and `make nixie` are green at HEAD. The Purpose's four proofs are all in place:
the behavioural scenarios (Work item 3), the `--check` envelope snapshots (Work
item 4), the entry-point e2e cases driving `stub.novel_compile()` (Work item 5),
and the agreement parametrized test pinning `(--check satisfied) ⇔
compile_consistent` over the corpus (Work item 4). `novel-compile --check` exits
`0` on a current tree and `4` on a stale or absent compile, writes nothing on any
path, and refuses an empty manifest with exit `3`.

CodeRabbit runs: WI1 — 0 findings; WI2/WI3 — rate-limited (exponential backoff
applied); the final combined run after WI6 returned 1 *minor* finding, against
the untracked planning artefact `docs/execplans/roadmap-4-1-2.review-r3.md`
(80-column rewrap). That file is not part of the 4.1.2 deliverable, is not
tracked, and `make markdownlint` passes on it (the repo config disables MD013),
so no change was made — the finding is outside the implemented scope and not a
repo gate.

No tolerance was breached: the footprint stayed within the expected files, the
`compiled_matches_drafts` signature and `CompiledComparison` enum were unchanged,
no new dependency was added, and no polarity ambiguity surfaced.

## Context and orientation

`novel-compile` is the deterministic compilation command. Its code lives in
`novel_ralph_skill/commands/_compile.py`; the console-script entry point is
`novel_ralph_skill/commands/stub.py::novel_compile`, which `_drive`s the app
through the shared `run` wrapper (`novel_ralph_skill/contract/runner.py`). The
app is built by `make_contract_app("novel-compile")` (the four-flag contract)
with a single `@app.default` body, `compile_manuscript`, that today only writes.

The comparison `--check` needs is already implemented once, shared by the
`novel-done` done predicate and the `novel-state check` §5.4 detector:

- `novel_ralph_skill/state/compile_model.py`:
  `compiled_matches_drafts(state, working_dir) -> CompiledComparison` returns
  `ABSENT` (no `compiled.md`), `MATCHES` (its bytes equal the ordered draft
  concatenation), or `DIVERGES` (present but unequal). It reads each present
  chapter's `draft.md` via `present_draft_bodies` and joins with
  `DRAFT_SEPARATOR` via `concatenate_drafts` — the same read/join rules the write
  path uses, so a freshly compiled tree is `MATCHES` by construction.
- `novel_ralph_skill/state/done_predicate.py::compile_consistent` projects that
  verdict to `is CompiledComparison.MATCHES` (line 271). `novel-compile --check`
  uses the **identical** projection.

Key terms:

- **Checker / mutator** (design §3.3): a checker writes nothing; a mutator may
  write `state.toml` or `compiled.md`. `novel-compile` is a mutator without the
  flag and a checker with `--check`.
- **The verdict polarity** (design §4.3/§4.2): `--check` and the
  `compile_consistent` clause treat only `MATCHES` as satisfied; the §5.4
  detector treats `ABSENT` as satisfied. All three read one helper.
- **Exit `4` (`ACTIONABLE_FINDING`)** (design §3.2): an actionable finding the
  agent must repair (here: regenerate `compiled.md`), distinct from the benign
  `1` the harness loops on.

The test corpus is `tests/working_corpus/` (re-exposed as fixtures by
`tests/conftest.py`). `WorkingTreeSpec.compiled` controls the on-disk
`compiled.md`: `None` (absent), `COMPILED_AUTO` (coherent), or an arbitrary
string (stale). Behavioural scenarios live in `tests/features/compile.feature`;
their step definitions live in `tests/steps/compile_steps.py`, and
`tests/test_compile_bdd.py` is only the binder (it calls
`scenarios("features/compile.feature")` and star-imports the steps). The
machine-mode envelope snapshot lives in `tests/test_compile_snapshots.py`. Note
that the existing BDD helper `_run_compile` (`tests/steps/compile_steps.py`) and
the snapshot helper `_drive` (`tests/test_compile_snapshots.py`) both hardcode
argv `[]` and thus drive the *write* path; `--check` tests must drive
`["--check"]` (see Work items 2–4 and Decision Log D-CHECK-ARGV).

## Plan of work

Five ordered, independently committable work items. Each ends with `make all`
green; the two doc-touching items also run `make markdownlint` and `make nixie`.

### Work item 1 — Add the `--check` read-only verdict body and wire the flag

What it implements: the design §4.3 `--check` checker and the §3.2/§3.3 exit-`4`
contract for `novel-compile`. Roadmap 4.1.2 ("report divergence by calling the
shared compile-and-hash routine from 3.1.2 … writing nothing and exiting 4 on
divergence").

Read first: design §4.3 (the `--check` paragraph), §3.2 (exit-code table, row 4),
§3.3 (checker/mutator table — `novel-compile --check` is a checker);
`docs/adr-001-deterministic-judgemental-boundary.md`;
`docs/adr-003-shared-interface-contract.md` (envelope, `result` vs `messages`,
exit codes); `docs/adr-005-command-surface-five-scripts.md` (the five-script
command surface and single-callback shape).
Skills to load: `python-router` → `python-errors-and-logging` (the exit-`3`
fault boundary and `raise … from …` discipline) and `python-types-and-apis`
(the kw-only flag signature, `CommandOutcome` return type); `leta` for
navigation. `domain-cli-and-daemons` for the operator-feedback shape.

Edits, all in `novel_ralph_skill/commands/_compile.py`:

1. Add a `_check_compiled` (or similarly named) function that:
   - loads `state.toml` via `_load_or_state_error(state_path())` (exit `3` on a
     bad state);
   - refuses an absent/empty `[chapters]` manifest with the same exit-`3`
     `StateInputError` and message the write path uses (the manifest guard is
     shared logic — factor the guard into a small helper both `compile_manuscript`
     and `_check_compiled` call, so the refusal cannot drift);
   - computes `verdict = compiled_matches_drafts(state, working_dir())`, wrapping
     the call in the same `try/except STATE_INPUT_ERRORS → StateInputError`
     boundary the write path wraps `present_draft_bodies` in, so an undecodable
     `draft.md`/`compiled.md` reaches exit `3`;
   - returns `CommandOutcome(code=ExitCode.SUCCESS, result={"checked":
     _COMPILED_REL, "chapters": len(state.chapters), "diverged": False},
     messages=[…])` when `verdict is CompiledComparison.MATCHES`;
   - otherwise (`ABSENT` or `DIVERGES`) returns `CommandOutcome(code=ExitCode.
     ACTIONABLE_FINDING, result={"checked": _COMPILED_REL, "chapters":
     len(state.chapters), "diverged": True}, messages=[…])`.
   - It must **not** call `write_text_atomically` and must not reach the write
     branch (D-POLARITY, R-NOWRITE).
2. Change the `@app.default` callback in `build_app` to `def _compile(*, check:
   bool = False)` and dispatch: `return _check_compiled() if check else
   compile_manuscript()`.
3. Import `CompiledComparison` and `compiled_matches_drafts` from
   `novel_ralph_skill.state` (confirm they are re-exported from the package
   `__init__`; if not, import from `compile_model` directly).
4. Update the module docstring and `build_app` docstring to record that
   `--check` is now wired and is a read-only checker (remove the "task 4.1.2;
   D-SCOPE out of scope" notes).

Tests in this item: none beyond keeping the suite green (tests land in items
2–4, per red-green). Run `make all`; the existing `test_compile_*` suites must
stay green and the new flag must not regress the write path.

Acceptance: `novel-compile --check` is reachable, returns a `CommandOutcome`, and
the write path is unchanged. Confirm by a throwaway manual run (not committed)
under a coherent tree (exit `0`) and a stale tree (exit `4`); the committed proof
is items 2–4.

### Work item 2 — Unit-test the verdict, fault boundary, and no-write guarantee

What it implements: the per-branch correctness and the read-only invariant of
the `--check` body (design §3.3, ADR-001; roadmap 4.1.2 success "writing
nothing").

Read first: AGENTS.md "Python verification and testing" (unit + unhappy-path +
edge cases; tests in `tests/`); `tests/test_compile_unit.py` and
`tests/test_compile_e2e.py` for the established patterns. Skills: `python-router`
→ `python-testing` (fixture/parametrize patterns, the no-write assertion).

Add `tests/test_compile_check_unit.py` (or extend `tests/test_compile_unit.py`
if it stays under the 400-line cap) driving `_check_compiled` / the built app
in-process via `run`.

**Critical driver requirement (do not copy the existing helpers verbatim).** The
write-path drivers — the behavioural helper `_run_compile` in
`tests/steps/compile_steps.py` and the snapshot helper `_drive` in
`tests/test_compile_snapshots.py` — both hardcode the argv as `[]`, which
exercises the *write* path. Every `--check` test in this and the following work
items must drive `run(build_app(), ["--check"], RunContext(command=
"novel-compile", working_dir="working", human=False))` — i.e. pass `["--check"]`,
**not** `[]`. Add a distinct `--check` driver (e.g. `_run_check`) rather than
reusing `_run_compile`/`_drive` unchanged; a copy that keeps `[]` would silently
test the write path and pass for the wrong reason, defeating both the no-write
and the verdict assertions. Confirm in each test that the argv carries `--check`.

The unit cases:

- `MATCHES` → exit `0`, `result["diverged"] is False`, `ok is True`,
  `result["checked"] == "working/manuscript/compiled.md"`, and **no**
  `compiled.md` mutation (snapshot the file's bytes and mtime before/after, or
  assert the bytes are byte-identical to the pre-existing coherent compile).
  Fixture: a coherent tree built with `compiled=COMPILED_AUTO`.
- `DIVERGES` (present-but-stale) → exit `4`, `result["diverged"] is True`,
  `ok is False`. Fixture: `WorkingTreeSpec(..., compiled="<stale bytes>")`, e.g.
  the corpus `DONE_PREDICATE_SOLE_STALE_COMPILE` shape or an inline stale string.
- `ABSENT` (no `compiled.md`) → exit `4`, `result["diverged"] is True`, **and**
  assert no `compiled.md` was created (R-NOWRITE: the checker must not write).
  Fixture: `compiled=None`.
- Empty/absent `[chapters]` manifest → exit `3`, no `compiled.md` written
  (mirrors `test_entry_point_compile_empty_manifest_exits_three`).
- Missing/unparseable `state.toml` → exit `3`.
- A usage error: a stray positional (`novel-compile --check bogus`) → exit `2`
  via the runner's `CycloptsError` arm (pins D-FLAG so the kw-only flag did not
  loosen positional handling).
- An undecodable/unreadable `compiled.md` or `draft.md` → exit `3` (the fault
  boundary; mirror the write path's read-fault unit test if one exists).

Acceptance: each test fails before Work item 1's branch is correct and passes
after; `make all` green. Every `--check` test asserts the on-disk `compiled.md`
is unchanged on its path (the no-write invariant), with at least the `ABSENT`
case asserting the file was not *created*.

### Work item 3 — Add the behavioural scenarios to `compile.feature`

What it implements: the externally observable `--check` workflow (AGENTS.md
"Add end-to-end tests where a change affects … command-line behaviour"; design
§4.3).

Read first: `tests/features/compile.feature` (the scenario text);
`tests/steps/compile_steps.py` (the actual `@given`/`@when`/`@then` definitions,
the `_Outcome` fixture, the `_run_compile` helper); `tests/test_compile_bdd.py`
(the scenario *binder* — it only calls `scenarios("features/compile.feature")`
and `from steps.compile_steps import *`); AGENTS.md behavioural-test rules.
Skills: `python-router` → `python-testing` (pytest-bdd step reuse).

**File routing (do not add steps to the binder).** `tests/test_compile_bdd.py`
is a binder only: it star-imports the step callables from `steps.compile_steps`
so `scenarios` can discover them. The `@given`/`@when`/`@then` definitions live
in `tests/steps/compile_steps.py`. Therefore:

- Add the new **scenario text** to `tests/features/compile.feature`.
- Add the new **step definitions** to `tests/steps/compile_steps.py` (the star
  import makes them visible to the binder automatically; `test_compile_bdd.py` is
  not edited). Adding steps to `test_compile_bdd.py` would put them outside the
  star-imported namespace pytest-bdd binds from and the scenarios would not bind.

**Driver requirement.** The existing `_run_compile` in `compile_steps.py`
hardcodes argv `[]` (the write path). Add a distinct `--check` runner — e.g.
`_run_check(working, monkeypatch)` that calls `run(build_app(), ["--check"],
RunContext(command="novel-compile", working_dir="working", human=False))` — and
a new `@when("novel-compile --check runs against that tree")` step invoking it.
Do **not** reuse the `[]`-argv `_run_compile`; reusing it would exercise the
write path and the `diverged`/no-write assertions would pass for the wrong reason.

Scenarios to add to `tests/features/compile.feature`:

- "check reports a current compile" — Given a coherent tree whose `compiled.md`
  matches the drafts, When `novel-compile --check` runs, Then it exits `0`, the
  envelope reports `diverged: false`, and `compiled.md` is byte-for-byte
  unchanged.
- "check reports a stale compile" — Given a tree with a present-but-stale
  `compiled.md`, When `novel-compile --check` runs, Then it exits `4`, the
  envelope reports `diverged: true`, and the present `compiled.md` is left
  byte-for-byte unchanged.
- "check reports an absent compile" — Given a tree with no `compiled.md`, When
  `novel-compile --check` runs, Then it exits `4`, `diverged: true`, and no
  `compiled.md` was created.
- "check refuses an empty manifest with exit 3" — reuse the existing empty-
  manifest Given; Then `novel-compile --check` exits `3` and writes no
  `compiled.md` (the existing not-exists Then is correct here — premise tree has
  no `compiled.md`).

Steps to add to `tests/steps/compile_steps.py`:

- A `@given` building a coherent tree with `compiled=COMPILED_AUTO` (the
  hash-equal coherent compile → `MATCHES`), returning an `_Outcome`. The existing
  stale-compiled Given writes deliberately stale bytes and is **not** coherent,
  so it cannot serve the "current compile" scenario; add a coherent Given.
- A `@given` building a present-but-stale tree (`compiled=<stale bytes>` /
  `DONE_PREDICATE_SOLE_STALE_COMPILE` shape) → `DIVERGES`.
- A `@given` building an absent-compile tree (`compiled=None`) → `ABSENT`.
- The `--check` `@when` step (the `_run_check` driver above).
- A `@then` asserting `diverged: false` and exit `0` (the current scenario) and
  a `@then` asserting `diverged: true` and exit `4` (the stale/absent scenarios),
  reading the captured exit code from `_Outcome`. To read `diverged` the `_when`
  must capture the rendered envelope (redirect stdout like `test_compile_snapshots`
  does, parse the JSON `result["diverged"]`), or assert exit code alone if the
  envelope is not captured at the BDD level — capture it so the `diverged` field
  is pinned behaviourally.

No-write Thens (the review's blocking point #2):

- The **absent** scenario reuses the existing `@then("no compiled.md is written")`
  (`asserts_no_compiled`, which asserts `not compiled.exists()`) — correct,
  because the absent tree has no `compiled.md` to begin with.
- The **stale** scenario must **not** reuse `asserts_no_compiled`: in the stale
  case `compiled.md` is *present* and must be left byte-for-byte unchanged, so
  `not compiled.exists()` is false and would mis-pass/fail. Add a **new** Then,
  e.g. `@then("the present compiled.md is left byte-for-byte unchanged")`, that
  captures the file's bytes in the `@given` (store them on `_Outcome`, read at
  build time before any run) and asserts the post-run bytes equal them. This
  pins the no-write invariant on the *present-but-stale* path, which the
  not-exists step cannot express. The current scenario reuses this same new Then.

Reuse where genuinely safe: the empty-manifest Given and the not-exists Then for
the absent/empty cases; the exit-`3` Then. Everything else is new.

Acceptance: the new scenarios bind and pass; `make all` green. The stale scenario
asserts the present `compiled.md` is byte-for-byte unchanged and the absent
scenario asserts it was not created, closing R-NOWRITE at the behavioural level
on both the present and absent paths.

### Work item 4 — Pin `--check` ⇔ `compile_consistent` agreement and snapshot the envelopes

What it implements: the roadmap 4.1.2 *headline* success criterion — "`novel-
compile --check` and the `novel-done` compile clause agree on every corpus
fixture because they share one routine (the compile-fidelity property)" — plus
the machine-mode envelope contract (design §9 snapshot rule).

Read first: roadmap 4.1.2 success; `tests/test_compile_snapshots.py` (snapshot
pattern, `result == {…}` semantic pairing, deterministic-token rule);
`tests/test_compiled_matches_drafts.py` and `tests/test_done_predicate.py` for
the clause's corpus usage. Skills: `python-router` → `python-verification` to
confirm the adversary, then `hypothesis` for the property; `python-testing` for
the snapshot. Load `python-verification` first; if the agreement is a finite
enumeration over the named corpus specs rather than a generated input space,
a parametrized table test is the right tool and Hypothesis is **not** required —
record that choice in the test docstring (AGENTS.md: property tests when a change
"introduces an invariant over a range of inputs, states, … or transitions").

Add `tests/test_compile_check_agreement.py`:

- The agreement invariant (R-AGREE): for every corpus tree spanning the three
  verdicts — at minimum `DONE_PREDICATE_ALL_HOLD` (`MATCHES`),
  `DONE_PREDICATE_SOLE_STALE_COMPILE` (`DIVERGES`), and an absent-compile spec
  (`dc.replace(DONE_PREDICATE_ALL_HOLD, compiled=None)` → `ABSENT`) — assert that
  `novel-compile --check`'s satisfied/finding verdict equals
  `compile_consistent(state, working_dir)`: `--check` exits `0` **iff** the
  clause is `True`, and exits `4` **iff** the clause is `False`. Build it as a
  parametrized test over the named specs; if a Hypothesis strategy over
  `WorkingTreeSpec.compiled` (`None` | `COMPILED_AUTO` | arbitrary-text) is
  cleaner, use `python-router` → `hypothesis` and a `@given` strategy, filtering
  nothing (no filtering trap). Either way the assertion is the biconditional
  `(--check satisfied) ⇔ compile_consistent`. The `--check` side of the
  biconditional must drive `run(build_app(), ["--check"], …)` (argv `["--check"]`,
  not `[]`) so the exit code being compared is genuinely the checker's; a `[]`
  argv would compare the write path's exit `0` against the clause and pass for the
  wrong reason on every fixture.

Add the `--check` envelope snapshots to `tests/test_compile_snapshots.py` (or a
sibling `tests/test_compile_check_snapshots.py`). **Driver requirement:** the
existing `_drive` helper in `test_compile_snapshots.py` hardcodes argv `[]` (the
write path); the `--check` snapshot driver must pass `["--check"]` to `run`, not
`[]`. Add a distinct `--check` driver rather than reusing `_drive` unchanged; a
`[]`-argv copy would snapshot the write envelope and the `diverged` field would
never appear.

The snapshots:

- the `MATCHES` envelope (exit `0`, `diverged: false`) and the `DIVERGES`
  envelope (exit `4`, `diverged: true`), each paired with a semantic assertion on
  the exit code, `ok`, and `result` (per AGENTS.md: snapshots paired with
  semantic assertions, no nondeterministic fields — the `checked` token is the
  working-relative constant and needs no normalisation, exactly like the write
  snapshot's `compiled` token).

Acceptance: the agreement test passes over every chosen corpus spec; the
snapshots are accepted (`--snapshot-update` once, then committed) and re-run
clean; `make all` green.

### Work item 5 — Pin the entry-point path with `--check` e2e cases

What it implements: the Purpose's third proof — an end-to-end test driving the
real console-script body. This is the only layer that exercises
`parse_global_flags` + `_drive` (`novel_ralph_skill/commands/stub.py:100-105`),
where `--human` is stripped and the residual argv (including `--check`) is
forwarded to `run`. The in-process tests in Work items 2–4 bypass this layer
entirely. (AGENTS.md "Add end-to-end tests where a change affects … command-line
behaviour"; design §4.3; R-ENTRYPOINT, D-ENTRYPOINT.)

Read first: `tests/test_compile_e2e.py` in full — the established entry-point
pattern is `monkeypatch.chdir(working.parent)`, `monkeypatch.setattr(sys,
"argv", [_COMMAND])`, then `stub.novel_compile()` inside `pytest.raises(
SystemExit)`, asserting `excinfo.value.code` and parsing the envelope from
`capsys`; the `_drafting_tree` helper there builds a coherent three-chapter tree
and returns the expected compiled bytes. Also read
`novel_ralph_skill/commands/stub.py` (`_drive`, `novel_compile`) and
`novel_ralph_skill/contract/runner.py:84-111` (`parse_global_flags`) to confirm
`--check` is forwarded unchanged. Skills: `python-router` → `python-testing`
(entry-point e2e via `monkeypatch.setattr(sys, "argv", …)` and `capsys`);
`leta` for navigation.

Add two cases to `tests/test_compile_e2e.py` (the suite the round-3 reviewer
named), each driving the real console-script body — **not** `run(build_app(),
…)`:

- `test_entry_point_compile_check_current_exits_zero`: build a coherent tree
  with `compiled.md` materialised to the expected concatenation (extend or
  reuse `_drafting_tree`, then write the coherent `compiled.md`, or build the
  corpus coherent spec with `compiled=COMPILED_AUTO`). Set `sys.argv =
  [_COMMAND, "--check"]`, call `stub.novel_compile()`, assert
  `excinfo.value.code == ExitCode.SUCCESS`, parse the envelope, assert
  `result["diverged"] is False` and `result["checked"] ==
  "working/manuscript/compiled.md"`, and assert `compiled.md` is byte-for-byte
  unchanged (the entry-point path must not write either).
- `test_entry_point_compile_check_stale_exits_four`: build a tree whose
  `compiled.md` is present but stale (the diverging bytes). Set `sys.argv =
  [_COMMAND, "--check"]`, call `stub.novel_compile()`, assert
  `excinfo.value.code == ExitCode.ACTIONABLE_FINDING` (exit `4`), parse the
  envelope, assert `ok is False` and `result["diverged"] is True`, and assert
  the present `compiled.md` is left byte-for-byte unchanged.

These two cases pin that the kw-only `--check` flag survives the
`parse_global_flags` + `_drive` pre-parse and reaches the body with the correct
verdict on both the satisfied (exit `0`) and finding (exit `4`) branches, closing
the round-3 gap: a future
change to argv forwarding that mishandled `--check` would now fail here even
though every in-process `run(build_app(), ["--check"], …)` test would still
pass.

Tests in this item: the two e2e cases above. No production code changes (Work
item 1 already wired the flag); this item is the entry-point regression pin.

Acceptance: both e2e cases fail before Work item 1's flag wiring is correct and
pass after; they drive `stub.novel_compile()` (not `run(build_app(), …)`); the
coherent case exits `0` with `diverged: false` and the stale case exits `4` with
`diverged: true`, each leaving `compiled.md` byte-for-byte unchanged. `make all`
green.

### Work item 6 — Update the developers' guide and users' guide

What it implements: AGENTS.md documentation gates ("Update `docs/users-guide.md`
for any change to application behaviour"; document internal conventions in
`docs/developers-guide.md").

Read first: `docs/users-guide.md` lines 83-100 (the `novel-compile` section) and
315-337 (the `compile_consistent` clause and exit codes);
`docs/developers-guide.md` lines 170-172, 204-216, 316-331, 559-625 (the compile
write path, the checker/mutator split, the shared-comparison-owner note, the done
clause). Skills: `en-gb-oxendict` for the prose; `df12-copy` is **not** needed
(this is internal/user reference, not marketing).

Edits:

- `docs/users-guide.md`: in the `novel-compile` section, document the `--check`
  flag — read-only, reports divergence, exits `0` when current and `4` when
  stale **or absent**, writes nothing. State that it agrees with the `novel-done`
  `compile_consistent` clause.
- `docs/developers-guide.md` line ~170-172: remove "the `--check` read-only
  divergence checker is roadmap task 4.1.2 and is not yet" — it is now delivered.
- `docs/developers-guide.md` lines ~327-331: correct "call the same compile-and-
  **hash** routine … that routine is not yet delivered, and `--check` is not yet
  wired" to state that both `novel-compile --check` and the `compile_consistent`
  clause now call the one `compile_model.compiled_matches_drafts` routine (a
  direct byte comparison, not a digest — D-BYTE-COMPARE), and that `--check`
  projects only `MATCHES` to satisfied (exit `0`), so an absent or stale
  `compiled.md` is exit `4`.
- Note the polarity contrast in the developers-guide: `novel-compile --check`
  and `compile_consistent` share the `MATCHES`-only polarity, *opposite* to the
  §5.4 `novel-state check` detector (absent = satisfied), reconciled in the one
  helper.

Wrap prose at 80 columns; code blocks at 120. Run `make markdownlint` and
`make nixie` in addition to `make all`.

Acceptance: both guides describe the delivered `--check` behaviour with no
"not yet" residue; `make markdownlint`, `make nixie`, and `make all` all green.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-4-1-2`.

1. Confirm the branch leaf and a clean tree:

   ```bash
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-4-1-2 \
     branch --show-current   # roadmap-4-1-2
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-4-1-2 status
   ```

2. Implement Work item 1, then run the gate and commit:

   ```bash
   make all
   git add -A && git commit   # file-based message; see commit-message skill
   ```

3. Implement Work items 2, 3, 4, 5 each as its own red-green commit, running
   `make all` before each commit. For Work item 4's snapshots, accept once:

   ```bash
   uv run pytest tests/test_compile_check_snapshots.py --snapshot-update
   uv run pytest tests/test_compile_check_snapshots.py   # re-run clean
   make all
   ```

4. Implement Work item 6, then run the Markdown gates and the full gate:

   ```bash
   make markdownlint
   make nixie
   make all
   git add -A && git commit
   ```

Expected `make all` transcript tail on success:

```plaintext
… passed in …s
```

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes. New behaviour is pinned by (a) unit tests for the
  three verdicts, the exit-`3` fault boundary, the exit-`2` usage error, and the
  no-write invariant (Work item 2); (b) four behavioural scenarios in
  `compile.feature` (Work item 3); (c) the agreement property/parametrized test
  proving `(--check satisfied) ⇔ compile_consistent` over the corpus and the
  `--check` envelope snapshots (Work item 4); (d) two end-to-end entry-point
  cases driving `stub.novel_compile()` with `sys.argv = ["novel-compile",
  "--check"]` over a coherent tree (exit `0`, `diverged: false`) and a stale tree
  (exit `4`, `diverged: true`), pinning `parse_global_flags` + `_drive` argv
  forwarding (Work item 5). Each new test fails before its implementation and
  passes after.
- Lint/typecheck: `make lint` and `make typecheck` (folded into `make all`) pass,
  including 100% docstring coverage via `interrogate`.
- Docs: `make markdownlint` and `make nixie` pass after Work item 5.
- Behaviour: `novel-compile --check` exits `0` on a current tree and `4` on a
  stale or absent compile, writes nothing on any path, and refuses an empty
  manifest with exit `3` — observable through the entry point and the envelope.

Quality method:

- `make all` (build, check-fmt, lint, typecheck, test) after every work item.
- `make markdownlint` and `make nixie` after the doc work item.
- The agreement test is the load-bearing acceptance: it falsifies any future
  drift between `--check` and `compile_consistent`.

## Idempotence and recovery

Every step is re-runnable. `make all` is idempotent. Snapshot acceptance is a
one-shot `--snapshot-update` followed by a clean re-run; if a snapshot churns,
narrow the captured output (do not blanket-accept). No step writes outside the
worktree, and `--check` itself writes nothing, so a failed `--check` test run
leaves no `compiled.md` artefact to clean up. If a commit's gate fails, fix
forward or `git restore` the work item's files and retry; no destructive history
rewrite is needed.

## Interfaces and dependencies

Reuse, do not re-implement:

- `novel_ralph_skill.state.compile_model.compiled_matches_drafts(state: State,
  working_dir: Path) -> CompiledComparison` — the single verdict site.
- `novel_ralph_skill.state.compile_model.CompiledComparison` — `ABSENT` /
  `MATCHES` / `DIVERGES`.
- `novel_ralph_skill.commands.novel_state`: `_load_or_state_error`, `state_path`,
  `working_dir`, `STATE_INPUT_ERRORS` — the shared exit-`3` boundary.
- `novel_ralph_skill.contract.runner`: `CommandOutcome`, `StateInputError`,
  `make_contract_app`; `novel_ralph_skill.contract.exit_codes.ExitCode`.

New/changed signatures at the end of this milestone, in
`novel_ralph_skill/commands/_compile.py`:

```python
def check_compiled() -> CommandOutcome:
    """Report whether compiled.md matches the drafts; write nothing.

    Exit 0 when the shared verdict is CompiledComparison.MATCHES; exit 4
    (ACTIONABLE_FINDING) when ABSENT or DIVERGES; exit 3 on a state/input fault
    or an absent/empty chapter manifest.
    """

# build_app's default callback gains a kw-only flag:
@app.default
def _compile(*, check: bool = False) -> CommandOutcome:
    return check_compiled() if check else compile_manuscript()
```

No new external dependency. No change to `pyproject.toml` (the console script
already routes through `stub.novel_compile`). No change to the shared
`compiled_matches_drafts` helper, the `CompiledComparison` enum, or the
`run`/envelope machinery.

## Revision note

Revision 3 (2026-06-24, planning agent) — resolved the round-3 blocking point:
the Purpose promised four proofs, one being "an end-to-end entry-point test", but
no work item delivered it; Work items 2–4 all drove the command in-process via
`run(build_app(), ["--check"], …)`, none drove the real console-script body
`stub.novel_compile()`. That in-process path bypasses `parse_global_flags` +
`_drive` (`stub.py:100-105`), the only layer where `--human` is stripped and the
residual argv (including `--check`) is forwarded to `run`, so a regression there
would pass every in-process test yet break the real path. Fix: added a dedicated
**Work item 5** that adds two `--check` cases to `tests/test_compile_e2e.py`
driving `stub.novel_compile()` with `sys.argv = ["novel-compile", "--check"]`
(coherent → exit `0`, `diverged: false`; stale → exit `4`, `diverged: true`),
mirroring the module's established `monkeypatch.setattr(sys, "argv", [_COMMAND])`
pattern; renumbered the docs item to Work item 6; rewrote the Purpose so its
four-proof list maps each proof to the work item that delivers it; added risk
R-ENTRYPOINT and Decision Log D-ENTRYPOINT. Verified against the sources that
`parse_global_flags` filters only `_HUMAN_FLAG` and returns every other token in
the residual argv (`runner.py:109-111`), so `--check` is forwarded unchanged
today; the new e2e cases are the regression pin for that behaviour. No change to
the implementation design (Work item 1), the shared-routine reuse, the polarity,
or the cyclopts flag binding.

Revision 2 (2026-06-24, planning agent) — resolved the design reviewer's three
blocking points by verifying each against the actual test sources:

- **Step file routing (D-STEP-FILE).** Work item 3 now directs new step
  definitions to `tests/steps/compile_steps.py` (where the `@given`/`@when`/`@then`
  callables actually live) and only new scenario text to
  `tests/features/compile.feature`; `tests/test_compile_bdd.py` is the binder and
  is not edited. Confirmed by reading both files: the binder calls
  `scenarios("features/compile.feature")` and `from steps.compile_steps import *`.
- **Stale-path no-write Then (D-STALE-NOWRITE).** Work item 3 now adds a distinct
  Then for the present-but-stale path that captures `compiled.md`'s bytes before
  the run and asserts them unchanged, instead of reusing `asserts_no_compiled`
  (which asserts `not compiled.exists()`, false when the file is present).
  Confirmed `asserts_no_compiled` asserts `not compiled.exists()` at
  `tests/steps/compile_steps.py`.
- **`--check` argv driver (D-CHECK-ARGV).** Work items 2, 3, and 4 now state that
  every `--check` test must drive `run(build_app(), ["--check"], …)` with a
  dedicated driver, because the existing `_run_compile` and `_drive` helpers
  hardcode argv `[]` (the write path). Confirmed both helpers pass `[]` to `run`.

These changes touch only the test-authoring guidance (Work items 2–4), the
Context and orientation note, and the Decision Log; the implementation design
(Work item 1, the shared-routine reuse, the polarity, and the cyclopts flag
binding) is unchanged.
