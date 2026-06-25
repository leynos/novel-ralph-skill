# Decide and pin the desloppify clean-pass findings contract

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DRAFT (revised round 3)

## Purpose / big picture

Roadmap task 7.1.3 settles a single payload-contract question before the
multi-pack detection surface grows: when `desloppify` finishes a scan, does the
machine-mode JSON envelope's `result.findings` list carry **every rule in the
pack** (including rules with `count: 0` that are well within threshold — the
"full audit trail"), or **only the over-threshold findings** (the
"violations-only" slimming)?

Today both detection projections serialise the full audit trail. In
`novel_ralph_skill/commands/_desloppify_report.py`, `report_outcome` emits
`"findings": [_finding_payload(finding) for finding in report.findings]` — one
entry per rule, passing or not. In `novel_ralph_skill/ledger/report.py`,
`ledger_report_outcome` does the same for every device. For the single shipped
§6 `offenders.toml` pack this is harmless, but it grows linearly as the
`ai-isms.toml` (roadmap 7.1.1) and `device-ledger.toml` (roadmap 7.1.2) packs
ship and as the multi-pack run surface (7.1.6/7.1.7) combines them: a clean scan
over three packs would serialise dozens of `count: 0` rows the harness never
reads. The roadmap entry exists so this decision is made **once, deliberately,
before** the multi-pack surface lands, so the per-hit payload contract the §7.1
packs inherit is not churned later.

After this change a reader can observe the decision three ways. First, the
decision and its rationale are written into the design (or developers' guide) as
the authoritative contract. Second, `desloppify` and `desloppify --ledger` emit
the chosen `findings` shape on a clean pass, demonstrable by running each over a
slop-free manuscript and reading the envelope. Third, the
suites that read the full trail (`tests/test_desloppify_snapshots.py`,
`tests/test_ledger_snapshots.py`, and the cross-command shape matrix
`tests/test_command_surface_matrix.py`) pin the chosen shape, so the contract is
regression-guarded and a future drift fails a test rather than slipping through
review.

This is a decision-and-conformance task, not a feature. The bulk of the work is
recording a justified contract and making the two existing projections plus
their snapshots agree with it. No new command, flag, library, or schema field is
introduced.

## The decision (proposed default, to be ratified in Work item 1)

The plan proposes, and Work item 1 ratifies, the **violations-only** contract:
`result.findings` carries only the over-threshold (failing) findings; the
machine-actionable `result.violations` slug list and the `ok`/exit-code remain
unchanged, so a clean pass emits `findings: []` and `violations: []`.

Rationale (recorded here so the implementer does not re-litigate it; Work item 1
captures the same rationale in the design):

1. The design's envelope contract (§3.1) states `result` "holds the
   command-specific structured payload and **every machine-actionable datum**:
   the names of failed clauses, rule ids and hit counts". A rule at `count: 0`
   within threshold is, by construction, not machine-actionable: the harness
   gates on `ok` and reads `result.violations` (§3.3, the checker read shape);
   it never needs the passing rules enumerated. The full audit trail is
   human-audit data, and `messages` already carries the human prose. So the
   slimmer shape is the one §3.1 actually describes.
2. The payload grows linearly with pack size and pack count. Violations-only
   makes a clean multi-pack scan emit `findings: []` regardless of how many
   rules ship, which is the scaling property the roadmap entry asks us to settle
   before the surface grows.
3. The information a slimmed clean pass drops — "rule X ran and found nothing" —
   is recoverable: the pack is versioned data the operator already owns, and a
   non-clean finding still lists every offending rule in full. No *runtime*
   consumer in the repository reads passing findings: the skill and harness read
   `violations`/`ok` only (`grep -rn findings skill/` finds no envelope
   consumer). Three *test* consumers read the full `result.findings` trail and
   must be re-pinned to the slimmed shape — the two snapshot suites
   (`test_desloppify_snapshots.py`, `test_ledger_snapshots.py`) and the
   cross-command shape matrix `test_command_surface_matrix.py`. Re-pinning these
   is a mechanical snapshot/assertion update, not a behavioural change to a
   production consumer; Work item 0 enumerates them exhaustively and Work item 2
   updates all three together (see the corrected inventory below).

If Work item 1's review rejects violations-only in favour of the full audit
trail, the rest of the plan still applies with the filter inverted: the contract
is documented either way, and the snapshots pin whichever shape is ratified. The
plan does not leave the shape undecided — it proposes one, justifies it, and
gates ratification at Work item 1's review.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- The shared envelope shape `{command, schema_version, ok, working_dir, result,
  messages}` (design §3.1; ADR-003) must not change. Only the contents of
  `result.findings` are in scope.
- `result.violations` (the slug list the harness gates on) and the `ok` flag /
  exit-code contract (§3.2: 0 clean, 4 actionable finding) must be byte-for-byte
  unchanged. This task touches the *audit-trail* list only, never the gating
  data.
- The two detection cores must not change. `novel_ralph_skill/rulepack/detect.py`
  (`DetectionReport`, `RuleFinding`) and `novel_ralph_skill/ledger/detect.py`
  (`LedgerReport`, `DeviceFinding`) still aggregate **every** rule/device; the
  slimming is a *projection* concern, applied in the two `report.py` modules
  only. Detection stays a complete, pure aggregation so the count cannot drift
  (design §4.4, §6.3).
- Do not pre-empt sibling tasks. Adding a matched-text span (7.1.4) and the
  canonical finding projection (7.1.5) are out of scope; this task changes
  *which* findings appear, not *which fields* a finding carries.
- No new external dependency, command, flag, or pack-schema field.
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments, and
  commits (AGENTS.md).
- Each commit passes every gate in AGENTS.md ("Change quality and committing"):
  `make check-fmt`, `make lint`, `make typecheck`, `make test`, `make audit`;
  and for any `.md` change, `make markdownlint` and `make nixie`.
- No code file may exceed 400 lines (AGENTS.md). Both `report.py` modules are
  well under the cap; the change is a few lines each.

## Tolerances (exception triggers)

- Scope: if the implementation requires changes to more than 9 files or more
  than ~200 net lines of code, stop and escalate. The expected edit set is
  pre-counted at eight files and is in bounds: 2 source files
  (`_desloppify_report.py`, `ledger/report.py`), 3 snapshot `.ambr` files
  (`test_desloppify_snapshots.ambr`, `test_ledger_snapshots.ambr`,
  `test_command_surface_matrix.ambr`), 2 snapshot/assertion test modules
  (`test_desloppify_snapshots.py`, `test_ledger_snapshots.py`) and the matrix
  module (`test_command_surface_matrix.py`), plus 1 doc file and 1 new
  projection-level unit-test module. The threshold was raised from 6 to 9 in
  round 2 after the round-1 review found the third full-trail consumer
  (`test_command_surface_matrix.py` + its `.ambr`) that the original count
  omitted; the headroom is deliberate, not a licence to grow scope further.
- Detection-core edit: if satisfying the contract appears to require editing
  `rulepack/detect.py` or `ledger/detect.py` (the aggregation cores), stop and
  escalate — that signals the design has been misread (the cores must stay
  complete; only the projection slims).
- Gating drift: if any change would alter `result.violations`, `ok`, or an exit
  code for any input, stop and escalate — that is out of contract.
- Decision reversal: if Work item 1's review rejects the proposed
  violations-only default, record the ratified alternative in the Decision Log
  and proceed with the inverted filter; do not implement both shapes.
- Iterations: if the snapshot suites still fail after 3 update attempts, stop
  and escalate.
- Ambiguity: the three known test consumers of the full `result.findings`
  trail — `tests/test_desloppify_snapshots.py`,
  `tests/test_ledger_snapshots.py`, and
  `tests/test_command_surface_matrix.py::test_desloppify_shape_across_phases` —
  are **pre-resolved** in this plan as mechanical snapshot/assertion updates (see
  Work item 2); the implementer must update them, not escalate on them. This
  Tolerance fires only if Work item 0's exhaustive sweep finds a *fourth*
  consumer not listed here, **or** a *production* (non-test) reader of a passing
  finding in `novel_ralph_skill/` or `skill/`. Either of those would make the
  slimming a behavioural change to a live consumer rather than a pure trail trim,
  and warrants escalation.

## Risks

    - Risk: A full-trail consumer reads a passing finding out of
      `result.findings` and goes red when the passing entries disappear. This
      risk already materialised once: round-1 review found the third consumer
      `tests/test_command_surface_matrix.py::test_desloppify_shape_across_phases`
      (line 717, `len(result["findings"]) == 24` across eleven clean phases) plus
      its snapshot `tests/__snapshots__/test_command_surface_matrix.ambr` (the
      eleven `test_machine_envelope_matrix[desloppify-*]` blocks, 264 `rule_id`
      rows, all with empty `violations`), which the original plan omitted.
      Severity: high
      Likelihood: high (already realised for the known three; low for any
      further consumer)
      Mitigation: the three known full-trail test consumers
      (`test_desloppify_snapshots.py`, `test_ledger_snapshots.py`,
      `test_command_surface_matrix.py` + its `.ambr`) are enumerated in Work
      item 0 and updated together in Work item 2 — the matrix `== 24` assertion
      becomes the slimmed clean shape (`findings == []` with the `set(result)`
      membership unchanged) and all three `.ambr` files regenerate in the same
      commit. Work item 0 additionally runs an exhaustive `tests/` + source +
      `skill/` sweep to confirm no *fourth* full-trail or *production* consumer
      exists; finding one trips the Ambiguity Tolerance.

    - Risk: The snapshot suites churn in a way that hides a real regression
      behind an expected one, so the snapshot stops proving the contract.
      Severity: medium
      Likelihood: medium
      Mitigation: Each snapshot update is paired with a semantic assertion that
      independently pins the slimmed shape (the existing suites already follow
      AGENTS.md "avoid snapshot-only coverage"). Add an explicit assertion that
      a clean pass yields `findings == []`, so the snapshot is never the only
      guard for the slimming.

    - Risk: The decision is made but the two projections drift apart (one slims,
      one does not), leaving the §7.1 packs with an inconsistent contract.
      Severity: medium
      Likelihood: low
      Mitigation: Work item 2 changes both projections in one commit and the
      ledger clean-pass snapshot block is regenerated in the same task (the
      ledger over-ration block is unchanged because its sole finding is already
      the failing one — see Work item 2 test edit 2), so the two slimmed shapes
      are pinned together. A shared one-line helper docstring records the contract
      decision in both modules pointing at the same doc anchor.

    - Risk: A future maintainer cannot tell whether the slim shape is deliberate
      or an oversight.
      Severity: low
      Likelihood: medium
      Mitigation: Work item 1 writes the decision and rationale into the design
      (or developers' guide) with the roadmap-task reference, and both
      projection docstrings cite that anchor.

## Progress

    - [x] Work item 0: Confirm the findings-consumer inventory and ratify the
      decision input (no code change).
    - [x] Work item 1: Record the clean-pass findings contract in the design /
      developers' guide. Authoritative anchor is the new developers' guide
      section "The clean-pass findings contract (roadmap task 7.1.3)" (after the
      rule-pack `desloppify` description); the ledger section cross-references it.
    - [x] Work item 2: Make `desloppify` and `desloppify --ledger` emit the
      chosen findings shape; update and pin all three full-trail consumers (the
      two snapshot suites and the command-surface matrix) with semantic
      assertions and regenerate all three `.ambr` files. Both projections now
      build `findings` from the `failed` filter; the red-green ordering was
      confirmed (the three clean-pass assertions failed before the source edit
      and passed after); snapshot regeneration matched the plan exactly — the
      desloppify `.ambr` regenerated both blocks, the matrix `.ambr` regenerated
      only the eleven `desloppify-*` blocks, and the ledger `.ambr` regenerated
      only the clean block (the over-ration block was untouched). Added
      `tests/test_desloppify_report.py` with four projection-level unit tests
      (slimming and clean-pass for both paths). `make all` green.
    - [x] Work item 3: Cross-reference sweep — update the projection docstrings,
      the roadmap success criterion, and any guide prose that describes the old
      shape; final whole-suite gate. Projection docstrings were updated in Work
      item 2. The sweep refined the developers' guide rule-pack description
      (`result.findings` carries only the over-threshold subset, cross-referenced
      to the new contract section) and the users' guide exit-0 bullet (a clean
      pass carries `findings: []`). The roadmap 7.1.3 success criterion is
      deliberately decision-neutral and left as-is; the ratified shape is recorded
      in Outcomes below. The design doc carried no stale full-trail prose. `make
      all` green at HEAD.

## Surprises & discoveries

    - Observation: The exhaustive Work item 0 sweep confirmed the round-2/round-3
      inventory exactly — no fourth full-trail consumer and no production reader
      exist. The plan was accurate as written; implementation proceeds without
      escalation.
      Evidence: `grep -rn '\["findings"\]\|get("findings")' tests/ skill/
      novel_ralph_skill/` returned exactly the three predicted envelope-payload
      reads (`test_desloppify_snapshots.py:109,141`,
      `test_command_surface_matrix.py:717`, `test_ledger_snapshots.py:149`). All
      `skill/` hits are critic-notes prose; the `_compile.py` and
      `state/schema.py` source hits are docstring prose and critic-pass state
      counts, not the envelope payload.
      Impact: none — the violations-only contract is a pure trail trim, ratified
      at Work item 0 without Tolerance breach.

## Decision log

    - Decision: Propose the violations-only clean-pass contract as the default,
      to be ratified at Work item 1.
      Rationale: design §3.1 defines `result` as "every machine-actionable
      datum"; a passing rule is not machine-actionable (the harness gates on
      `ok`/`violations` per §3.3), so the slim shape is the one the contract
      already describes, and it is the shape that scales as packs multiply.
      Date/Author: 2026-06-25, planning agent.

    - Decision: Confine the change to the two `report.py` projection modules and
      leave both detection cores untouched.
      Rationale: detection must remain a complete pure aggregation so counts
      cannot drift (design §4.4, §6.3); slimming is a presentation choice that
      belongs at the envelope boundary, not in the aggregator.
      Date/Author: 2026-06-25, planning agent.

    - Decision: The complete full-trail `result.findings` consumer inventory is
      exactly three test sites (no production reader): (1)
      `tests/test_desloppify_snapshots.py` (lines 109, 141, plus its `.ambr`);
      (2) `tests/test_ledger_snapshots.py` (line 149, plus its `.ambr`); (3)
      `tests/test_command_surface_matrix.py::test_desloppify_shape_across_phases`
      (line 717, `len(result["findings"]) == 24`, plus
      `tests/__snapshots__/test_command_surface_matrix.ambr`). The clean cases in
      `tests/test_desloppify_command.py` (line ~199) and
      `tests/test_ai_isms_e2e.py` (line ~250) read `result["violations"]` only,
      not `findings`, so they are unaffected. The skill and harness read
      `violations`/`ok` only (`grep -rn findings skill/` finds no envelope
      reader). The remaining `findings` matches across `tests/` are detection-core
      reads (`report.findings` on `DetectionReport`/`LedgerReport`, e.g.
      `test_rulepack_detect.py`, `test_ledger_detect.py`, `test_ledger_properties.py`)
      or unrelated local variables (`_state_layout_scanner.py`,
      `test_done_predicate_blockers.py`) — none read the envelope payload.
      Rationale: round-1 review (B1) found the original plan's "only two
      consumers" premise false; this entry pins the corrected, exhaustive
      inventory (verified by `grep -rn 'findings' tests/ skill/
      novel_ralph_skill/` on 2026-06-25) so Work item 2 cannot leave a suite red.
      Date/Author: 2026-06-25, planning agent (round 2).

    - Decision: The ledger over-ration snapshot is **not** red-green under
      slimming and its `.ambr` block does not regenerate; the ledger slimming is
      proven solely by the clean-ledger snapshot collapsing to `findings: []`.
      Rationale: round-2 review (B1, Doggylump) found the plan falsely asserted a
      "passing sibling device" in the over-ration case. The `_LEDGER` fixture
      (`tests/test_ledger_snapshots.py:35-42`) defines exactly one device
      (`sternum`); the over-ration block (`tests/__snapshots__/
      test_ledger_snapshots.ambr` lines 40-82) is a single `passed: False`
      finding, which violations-only slimming keeps. `len(findings) == 1`
      therefore holds before and after and pins nothing about the slimming, so
      the misleading rationale was removed from
      `test_over_ration_envelope_snapshot`. Only
      `test_clean_ledger_envelope_snapshot` (a single passing `sternum`, `.ambr`
      lines 2-39) regenerates to `findings: []` and is the genuine red-green proof
      for the ledger path. Verified by reading the fixture and both `.ambr` blocks
      on 2026-06-25, and by `grep -c rule_id` confirming the desloppify one-hit
      block carries 24 rows (genuinely red-green there, unlike the ledger
      over-ration block's single row).
      Date/Author: 2026-06-25, planning agent (round 3).

    - Decision: Ratify the violations-only clean-pass contract (Work item 0).
      Rationale: the exhaustive sweep
      (`grep -rn '\["findings"\]\|get("findings")' tests/ skill/
      novel_ralph_skill/`, 2026-06-25) confirmed the full-trail envelope payload
      is read by exactly three test sites — `tests/test_desloppify_snapshots.py`
      (lines 109, 141), `tests/test_command_surface_matrix.py` (line 717), and
      `tests/test_ledger_snapshots.py` (line 149) — and no production consumer.
      The `skill/` `findings` hits are all critic-notes prose; the
      `novel_ralph_skill/commands/_compile.py` and
      `novel_ralph_skill/state/schema.py` hits are docstring prose and
      critic-pass blocker/major/minor counts, not the envelope payload. No
      fourth full-trail consumer and no production reader exist, so the Ambiguity
      Tolerance does not fire and violations-only stands as the ratified shape.
      Date/Author: 2026-06-25, implementation agent (Work item 0).

## Outcomes & retrospective

The **violations-only** clean-pass contract was ratified and survived review:
the Work item 0 sweep confirmed no production reader and no fourth full-trail
consumer, so the proposed default stood unchanged. `result.findings` now carries
only the over-threshold findings on both the rule-pack and the `--ledger` paths;
a clean pass emits `findings: []` and `violations: []` at exit `0`, while
`violations`, `ok`, and every exit code are byte-for-byte unchanged. The
detection cores were untouched — they still aggregate a finding for every
rule/device, and the slimming lives entirely in the two `report.py` projections.

Both projections and all three full-trail snapshot suites agree: the red-green
ordering was observed (the desloppify, ledger, and matrix clean-pass assertions
failed before the source edit and passed after), and snapshot regeneration
matched the plan exactly — the desloppify `.ambr` regenerated both blocks, the
matrix `.ambr` regenerated only the eleven `desloppify-*` blocks, and the ledger
`.ambr` regenerated only the clean block (the over-ration block kept its sole
failing finding). The new `tests/test_desloppify_report.py` pins the slimming at
the projection boundary for both paths. The contract is recorded in the
developers' guide ("The clean-pass findings contract") as the authoritative
anchor that the design, the ledger guide section, the users' guide, and both
projection docstrings reference. The multi-pack surface (7.1.6/7.1.7) inherits
this shape and does not re-litigate it.

The edit set landed at eight files plus the new projection-test module, within
the Scope Tolerance. No Tolerance fired. `make all` is green at HEAD.

## Context and orientation

Assume no prior knowledge of this repository. The relevant pieces:

- `desloppify` is one of five deterministic console-scripts. It reads a
  versioned TOML *rule pack* and reports prose-slop hits without editing or
  judging (design §4.4). It emits the shared JSON envelope
  `{command, schema_version, ok, working_dir, result, messages}` (design §3.1;
  `docs/adr-003-shared-interface-contract.md`). The harness reads `result` and
  `ok`; it never parses `messages`.
- The detection core is pure. `novel_ralph_skill/rulepack/detect.py` defines
  `RuleFinding` (one aggregated result per rule: `rule_id`, `pattern`, `count`,
  `threshold`, `basis`, `density`, `passed`, `lines`) and `DetectionReport`
  (`pack`, `total_words`, `findings`, `passed`). `detect(pack, chapters)`
  returns a finding for **every** rule in pack-authoring order.
- The envelope projection is separate. `report_outcome` in
  `novel_ralph_skill/commands/_desloppify_report.py` turns a `DetectionReport`
  into a `CommandOutcome`. Today it sets
  `result.findings = [_finding_payload(f) for f in report.findings]` (every
  rule) and `result.violations = [f.rule_id for f in failed]` (over-threshold
  only). This is the line the slimming changes.
- The ledger path mirrors this. Roadmap 7.1.2 added
  `desloppify --ledger`, whose projection `ledger_report_outcome` in
  `novel_ralph_skill/ledger/report.py` emits a full per-device audit trail and
  **explicitly defers the slimming decision to 7.1.3** (see that module's
  docstring: "The ledger payload carries a full audit trail … the round-1 review
  notes 7.1.3's clean-pass slimming may later revisit this, and the WI5 snapshot
  is the churn-absorbing seam"). This task is that revisit.
- The contract is regression-guarded by snapshot suites:
  `tests/test_desloppify_snapshots.py` (with `tests/__snapshots__/
  test_desloppify_snapshots.ambr`) and `tests/test_ledger_snapshots.py` (with
  its `.ambr`). Each snapshot is paired with semantic assertions so the snapshot
  is never the sole guard (AGENTS.md "avoid snapshot-only coverage"; design §9).
- A third suite also pins the full trail: the cross-command shape matrix
  `tests/test_command_surface_matrix.py`. Its
  `test_desloppify_shape_across_phases` (line 717) drives `desloppify` across all
  eleven workflow phases and hard-asserts `len(result["findings"]) == 24` (the
  full shipped pack) with `result["violations"] == []` on every phase — eleven
  clean passes. Its companion snapshot
  `tests/__snapshots__/test_command_surface_matrix.ambr` captures the same full
  trail in the eleven `test_machine_envelope_matrix[desloppify-*]` blocks (264
  `rule_id` rows total, every block with empty `violations`). Under
  violations-only slimming each of these eleven clean cases becomes
  `findings == []`, so the `== 24` assertion and all eleven snapshot blocks must
  be updated in Work item 2 (see B1 in the round-1 review). This consumer was
  missed in round 1 and is now first-class in the inventory.
- The behavioural / command / e2e tests
  (`tests/test_desloppify_command.py` line ~199, `tests/test_desloppify_e2e.py`,
  `tests/test_ai_isms_e2e.py` line ~250) assert on `result.violations` and `ok`,
  **not** on the full `findings` list, so they are robust to the slimming
  (verified: both clean cases read `result["violations"] == []`). The e2e tests
  drive the installed console-script through a cuprum catalogue (see below).

Terms of art, defined:

- *Full audit trail*: `result.findings` carries one entry per rule/device in the
  pack, passing or failing. The current behaviour.
- *Violations-only / slimmed*: `result.findings` carries only the
  over-threshold (failing) entries. A clean pass yields `findings: []`.
- *Projection*: the pure function that maps a detection report to the envelope
  payload, living in a `report.py` module. The slimming is applied here.

### cuprum and external-library pinning (e2e relevance)

The installed-binary e2e tests run the real console-script through **cuprum**,
the locked allowlisting subprocess wrapper at `/data/leynos/Projects/cuprum`. The
fixtures this task may touch use exactly these cuprum APIs, all verified against
the locked source:

- `cuprum.ProgramCatalogue` and `cuprum.ProjectSettings`
  (`cuprum/catalogue.py`: `class ProjectSettings` line 33, `class
  ProgramCatalogue` line 59) build the one-project allowlist; the e2e fixture
  `tests/installed_binary_fixtures.py:_one_program_catalogue` constructs
  `ProgramCatalogue(projects=(ProjectSettings(name=…, programs=(program,),
  documentation_locations=(), noise_rules=()),))`.
- `cuprum.program.Program` is the allowlisted executable token.
- `cuprum.sh.make(program, catalogue=…)` (`cuprum/sh.py:make`, line 528) returns
  the callable bound to the catalogue; calling it yields a `SafeCmd`
  (`cuprum/sh.py:349`).
- `SafeCmd.run_sync(...)` (`cuprum/sh.py:441`) returns a result whose
  `.exit_code: int` (`cuprum/sh.py:115`), `.stdout: str | None`
  (`cuprum/sh.py:163`), and `.stderr` are read by the fixtures.

**This task does not add or change any cuprum invocation.** The e2e tests assert
on `result.violations` and `ok`, which this task leaves unchanged, so no e2e
fixture or cuprum call needs editing. The cuprum surface is documented here only
to confirm that the e2e layer is *unaffected*: if implementation finds an e2e
test asserting on a *passing* finding's presence (it does not, per the pre-work
grep), that is a Tolerance breach to escalate, not a fixture edit to improvise.

No other locked external library's behaviour is load-bearing for this task.
Cyclopts (the CLI parser), `pytest-timeout`, `pytest-xdist`, and `uv`
resolution all sit underneath the existing command and test machinery, which
this task does not change: it edits two pure projection functions and their
snapshots. The plan therefore makes **no** new behavioural claim about those
libraries that would need firecrawl verification; the only behaviours it relies
on (envelope rendering via `render_machine`, snapshot capture via syrupy) are
already exercised by the green suites this task inherits.

## Plan of work

The work proceeds in four ordered, independently committable items. Work item 0
is a no-code confirmation gate; Work item 1 records the decision; Work item 2
implements and pins it; Work item 3 sweeps cross-references and runs the full
markdown + code gate.

### Work item 0 — Confirm the consumer inventory and ratify the decision input

No code change. The purpose is to make the slimming provably a pure trail trim,
not a behavioural change to a hidden consumer.

Implements: roadmap 7.1.3 "make the deliberate full-audit-trail-versus-
violations-only decision once"; design §3.1 (`result` is machine-actionable
data), §3.3 (checker read shape is `violations`).

Steps:

1. Run an **exhaustive** sweep — not just `skill/` (the round-1 plan's gap) but
   every directory — for reads of the envelope `findings` field. Run
   `grep -rn 'findings' tests/ skill/ novel_ralph_skill/` and `leta refs` for
   the `findings` attribute on `DetectionReport`/`LedgerReport`, plus a `grepai`
   sweep for JSON-consuming positions (`result["findings"]`, `["findings"]`,
   `.get("findings")`). Classify every hit as one of: envelope-payload read
   (in scope), detection-core read (`report.findings`, out of scope — the cores
   are untouched), or unrelated local variable. Record the full classified list
   in the Decision Log.
2. Confirm the full-trail *envelope-payload* consumers are exactly the three
   already pinned in the Decision Log inventory — `test_desloppify_snapshots.py`,
   `test_ledger_snapshots.py`, and
   `test_command_surface_matrix.py::test_desloppify_shape_across_phases` (with
   their three `.ambr` files) — and that the skill and harness read
   `violations`/`ok` only. The clean cases in `test_desloppify_command.py` and
   `test_ai_isms_e2e.py` read `violations`, not `findings`, and are unaffected.
   These three test consumers are **expected, mechanical updates** handled in
   Work item 2, **not** escalation triggers (Tolerance "Ambiguity" is
   pre-resolved for them). Escalate only if the sweep reveals a *fourth*
   full-trail consumer or any *production* (non-test) reader of a passing
   finding.
3. Record the ratified decision (violations-only, unless escalation overturns
   it) in the Decision Log with the §3.1/§3.3 rationale.

Docs to read: design §3.1 (envelope, `result`), §3.2 (exit codes), §3.3
(command/query segregation, the `violations` read shape), §4.4 (`desloppify`),
§6.1-§6.3 (rule-pack and device-ledger packs).

Skills to load: `leta` (refs/grep for the consumer inventory); `grepai`
(semantic sweep for envelope consumers). No code skill needed (no code change).

Tests: none (no code change). The deliverable is the Decision Log entry —
specifically the classified, exhaustive consumer inventory that names all three
full-trail test consumers and confirms no fourth or production reader exists.

Validation: this item commits only the updated ExecPlan. Run `make markdownlint`
and `make nixie` over the changed `.md`. No `make all` needed because no source
or test changed, but running `make all` is harmless and confirms a clean
baseline.

### Work item 1 — Record the clean-pass findings contract in the docs

Write the ratified decision into the authoritative documentation so the contract
is captured "in the design or developers' guide" (roadmap 7.1.3 success
criterion). The developers' guide "Rule packs and the loader boundary" section
(around `desloppify`'s `result` description, near
`docs/developers-guide.md:1044-1053`) is the natural home, with a one-line
cross-reference from design §4.4 if the design proves the better anchor;
implementer picks the single authoritative location and the other merely
references it (do not duplicate the normative statement).

Implements: roadmap 7.1.3 ("the contract is captured in the design or
developers' guide"); design §4.4, §6.2.

Content to write (the normative statement):

- State that `result.findings` carries **only over-threshold findings**; a clean
  pass emits `findings: []` and `violations: []` at exit 0.
- State the rationale in one or two sentences (machine-actionable data only, per
  §3.1; the audit trail is recoverable from the versioned pack and the
  non-clean envelope).
- State that the decision applies uniformly to both the rule-pack path and the
  `--ledger` path, so the §7.1 packs (ai-isms, device-ledger, and the future
  multi-pack run) inherit one shape.
- Note explicitly that this is the contract the multi-pack surface
  (7.1.6/7.1.7) inherits, so it is not re-litigated there.

Docs to read: `docs/developers-guide.md` "Rule packs and the loader boundary"
(lines ~966-1053) and "The device ledger and per-novel rationing" (line ~1113);
design §3.1, §4.4, §6.1-§6.3; `docs/documentation-style-guide.md` for prose
conventions; AGENTS.md "Documentation maintenance".

Skills to load: `en-gb-oxendict` (enforce Oxford spelling in the new prose).

Tests: none (documentation only).

Validation: `make markdownlint` and `make nixie` over the changed `.md` files;
both must pass. Commit the doc change alone so the contract lands before the code
conforms to it (the doc is the source of truth the code then satisfies).

### Work item 2 — Emit the chosen findings shape and pin it with snapshots

Make both projections emit the slimmed `findings` list, update all three
full-trail consumer suites (the two snapshot suites plus the command-surface
shape matrix), and add a semantic assertion that a clean pass yields
`findings == []` so the snapshot is never the sole guard.

Implements: roadmap 7.1.3 ("7.1.1/7.1.2 emit the chosen shape"); design §3.1,
§4.4, §9 (snapshot coverage of the envelope plus boundary examples).

Source edits (both in one commit, so the two paths cannot drift):

1. `novel_ralph_skill/commands/_desloppify_report.py`, in `report_outcome`
   (current line 182): change
   `"findings": [_finding_payload(finding) for finding in report.findings]`
   to project from the already-computed `failed` list (the over-threshold
   findings), so the slimmed list is built from the same filter that feeds
   `violations`. The `violations`, `pack`, `total_words`, `ok`, and exit-code
   are untouched. Update the function and module docstrings to state the slimmed
   contract and cite the Work item 1 doc anchor.
2. `novel_ralph_skill/ledger/report.py`, in `ledger_report_outcome`
   (current line 131): the same change — project `findings` from the `failed`
   list rather than `report.findings`. Update the module docstring (which today
   says "carries a full audit trail … 7.1.3's clean-pass slimming may later
   revisit this") to record that 7.1.3 has now slimmed it, citing the same
   anchor.

Detection cores (`rulepack/detect.py`, `ledger/detect.py`) are **not** touched:
they still aggregate every rule/device; only the projection slims (Constraint).

Test edits:

1. `tests/test_desloppify_snapshots.py`:
   - `test_clean_pass_envelope_snapshot`: add an explicit semantic assertion
     `assert result["findings"] == []` (the slimmed clean-pass shape), so the
     snapshot is paired with a behavioural guard for the slimming specifically.
     Note: this test's existing `for finding in findings: assert
     isinstance(finding["basis"], str)` loop becomes a no-op once `findings` is
     empty, so the new explicit `== []` assertion is load-bearing — without it
     the slimming would be snapshot-only here (AGENTS.md "avoid snapshot-only
     coverage"). Regenerate the snapshot (`tests/__snapshots__/
     test_desloppify_snapshots.ambr`) so the clean-pass envelope now shows an
     empty `findings` list.
   - `test_one_hit_past_threshold_envelope_snapshot`: this case has exactly one
     over-threshold rule, so its `findings` list now contains exactly that one
     `smirked` finding (no passing rules). Add `assert len(findings) == 1` and
     keep the existing `phrase`/`lines`/`basis` assertions on the `smirked`
     entry; regenerate the snapshot.
2. `tests/test_ledger_snapshots.py`: the ledger path differs in an important way
   from the desloppify path, because the `_LEDGER` fixture
   (`tests/test_ledger_snapshots.py:35-42`) defines exactly **one** device
   (`sternum`); there is no sibling device. The two cases therefore behave
   asymmetrically under slimming:
   - `test_clean_ledger_envelope_snapshot`: the within-ration scan currently
     emits a single **passing** `sternum` finding (the
     `tests/__snapshots__/test_ledger_snapshots.ambr` clean block, lines 2-39,
     `passed: True`). Under violations-only slimming this passing finding drops
     out, so the clean ledger trail becomes `findings: []` and its `.ambr` block
     **regenerates**. This is the genuinely red-green case for the ledger path.
     The test today reads only `result["violations"]` and never touches
     `findings`; add an explicit `assert result["findings"] == []` so the clean
     ledger's slimmed trail is semantically guarded (this assertion fails before
     the source edit and passes after), then regenerate its block.
   - `test_over_ration_envelope_snapshot`: the over-ration scan's sole device is
     the **failing** `sternum` finding (the `.ambr` over-ration block, lines
     40-82, `passed: False`). Because that one finding is already over-threshold,
     violations-only slimming does **not** remove it: `findings` contains exactly
     the same single `sternum` entry before and after the change, so the
     over-ration `.ambr` block does **not** regenerate under this task. The
     existing `next(f for f in findings if f["device_id"] == "sternum")` extractor
     still resolves and its `count == 3` / `passed is False` / line-order
     assertions stand unchanged. Do **not** add `assert len(findings) == 1` to
     this test as a slimming proof: it would hold identically before and after
     (it is not red-green and pins nothing about the slimming, since the single
     device is the failing one). If a `len(findings) == 1` assertion is added at
     all, label it honestly as confirming the single-device fixture is present,
     not as evidence that slimming occurred. The ledger slimming is proven solely
     by `test_clean_ledger_envelope_snapshot` regenerating to `findings: []`.
3. `tests/test_command_surface_matrix.py::test_desloppify_shape_across_phases`
   (line 717): this is the third full-trail consumer the round-1 review (B1)
   surfaced. Change the per-phase assertion from
   `assert len(typ.cast("list[object]", result["findings"])) == 24` to
   `assert result["findings"] == []` — every one of the eleven phases is a clean
   pass (`violations == []`), so the slimmed shape is an empty trail on all of
   them. Keep the surrounding assertions unchanged: the `set(result) == {"pack",
   "total_words", "violations", "findings"}` membership check (the `findings` key
   still exists, now empty), `result["violations"] == []`, and the `total_words`
   per-phase expectation. Update the docstring sentence that today says "the full
   24-rule shipped pack on every phase" to describe the slimmed clean shape
   (`findings == []`; the 24-rule pack is still aggregated by the detection core,
   but the clean envelope no longer enumerates it). Then regenerate
   `tests/__snapshots__/test_command_surface_matrix.ambr`: the eleven
   `test_machine_envelope_matrix[desloppify-*]` blocks must each collapse their
   24-row `findings` list to an empty list (264 `rule_id` rows removed across the
   eleven blocks); the non-desloppify blocks in that file are untouched. This
   `.ambr` regenerates in the same Work item 2 commit as the other two so the
   three snapshots and the source stay in lockstep.
4. Add (or extend) one focused unit test asserting the slimming at the
   projection boundary directly, independent of the full command run, so the
   contract is pinned at the smallest unit: build a `DetectionReport` (or use an
   existing factory) with a mix of passing and failing findings and assert
   `report_outcome(report).result["findings"]` contains exactly the failing
   rule_ids while `result["violations"]` is unchanged. Place it in the existing
   `tests/test_desloppify_finding_message.py` neighbourhood or a new
   `tests/test_desloppify_report.py` if no projection-level module exists.
   Add the symmetric ledger-projection unit test for `ledger_report_outcome`.

Docs to read: design §9 (verification strategy: snapshot the machine envelope
plus boundary examples; "avoid snapshot-only coverage"); AGENTS.md "Change
quality and committing" (Python testing rules); `python-testing` skill for
syrupy snapshot regeneration discipline.

Skills to load: `python-router` then `python-data-shapes` (the finding payload
is a data shape and the change is which entries the projection emits);
`python-testing` (snapshot regeneration, pairing snapshots with semantic
assertions). No property-based or mutation tooling is warranted here: the change
is a deterministic list filter with a fixed, enumerable boundary (clean pass /
one-hit-past-threshold), which design §9 explicitly says `desloppify` covers
with snapshots plus boundary examples, **not** a property or mutation suite. If
during implementation the filter logic turns out to have a non-obvious boundary
(it should not — it is `if not finding.passed`), reconsider `hypothesis` via
`python-verification`; otherwise do not add it.

Validation: regenerate the snapshots with the project's snapshot-update
invocation (`pytest --snapshot-update tests/test_desloppify_snapshots.py
tests/test_ledger_snapshots.py tests/test_command_surface_matrix.py`), then run
the full `make all` gate (`make check-fmt`, `make lint`, `make typecheck`, `make
test`, `make audit`). Which `.ambr` blocks actually regenerate is asymmetric and
must be understood so a stray non-regeneration is not mistaken for a bug:

- `test_desloppify_snapshots.ambr`: **both** blocks regenerate — the clean block
  collapses 24 rows to `findings: []`, and the one-hit block collapses 24 rows to
  the single failing `smirked` finding.
- `test_command_surface_matrix.ambr`: the eleven
  `test_machine_envelope_matrix[desloppify-*]` blocks each collapse their 24-row
  `findings` list to empty; the non-desloppify blocks are untouched.
- `test_ledger_snapshots.ambr`: **only** the clean block regenerates (its sole
  passing `sternum` finding drops to `findings: []`). The over-ration block does
  **not** change, because its sole finding is already the failing one (see Work
  item 2 test edit 2). The ledger `.ambr` file is therefore still modified, but
  only in the clean-pass block.

The new clean-pass assertions (`findings == []` in the desloppify and ledger
snapshot suites, and the changed `== []` matrix assertion) must fail before the
source edit and pass after (red-green); confirm this by staging the test edits
first, observing the failures, then applying the projection edit. The
desloppify one-hit `len(findings) == 1` assertion is likewise red-green (24 → 1).
The ledger over-ration case is **not** red-green and is not part of the proof
(its findings are unchanged by slimming). Commit source, all three test modules,
and the modified `.ambr` files together so no full-trail consumer is left red.

### Work item 3 — Cross-reference sweep and final gate

Tidy every place that describes the old full-audit-trail shape so the
documentation is internally consistent, and run the complete gate including
markdown lint and nixie.

Implements: roadmap 7.1.3 success criterion (the contract is captured and the
emitters agree); AGENTS.md "Documentation maintenance" (proactively update
affected docs).

Steps:

1. Update the roadmap 7.1.3 entry's checkbox to done once merged is out of
   scope for this plan (the workflow owns merge), but ensure the success
   criterion wording in `docs/roadmap.md` still matches what was built; if the
   plan's ratified shape differs from the roadmap's neutral phrasing, leave the
   roadmap criterion as-is (it is deliberately decision-neutral) and record the
   chosen shape in the Outcomes section here.
2. Sweep the developers' guide and design for any prose that asserts the
   envelope "carries the full per-rule findings" or "every device's finding,
   including passing devices" (e.g. `_desloppify_report.py` and
   `ledger/report.py` docstrings already updated in Work item 2; the developers'
   guide line ~1049 "reports a per-rule finding"). Reword to the slimmed
   contract where the text claims a full trail; leave wording that merely
   describes a *finding's fields* untouched (that is 7.1.4/7.1.5 territory).
3. Confirm no stray reference still tells a reader to expect `count: 0` rows in
   a clean envelope.
4. Run the complete gate: `make all`, then `make markdownlint` and `make nixie`
   over every changed `.md`. All must pass.

Docs to read: `docs/developers-guide.md` (rule-pack and ledger sections),
`docs/novel-ralph-harness-design.md` §4.4/§6, `docs/roadmap.md` 7.1.3 entry.

Skills to load: `en-gb-oxendict` (prose), `leta`/`grepai` (find stale
descriptions).

Tests: none new; the suites from Work item 2 are the regression guard.

Validation: `make all` green; `make markdownlint` and `make nixie` green on all
`.md` changes. Update `Progress` and `Outcomes & retrospective`.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-1-3`.

Work item 0 (inventory):

    leta refs RuleFinding
    leta refs DetectionReport
    grepai search --workspace Projects --project novel-ralph-skill \
        "envelope result findings consumer" --toon --compact
    grep -rn 'findings' tests/ skill/ novel_ralph_skill/

Expect: the envelope-payload *writers* are `_desloppify_report.py` and
`ledger/report.py`; the full-trail *reader* consumers are exactly three test
sites — `tests/test_desloppify_snapshots.py`, `tests/test_ledger_snapshots.py`,
and `tests/test_command_surface_matrix.py::test_desloppify_shape_across_phases`
(line 717) — plus their three `.ambr` snapshots. Every other `findings` hit is a
detection-core `report.findings` read or an unrelated local. Record the full
classified list in the Decision Log.

Work item 1 (docs) and Work item 3 (sweep): edit the `.md` files, then:

    make markdownlint
    make nixie

Expect both to report success on the changed files.

Work item 2 (code + snapshots): after editing the two `report.py` modules and
the test modules, regenerate and gate:

    pytest --snapshot-update \
        tests/test_desloppify_snapshots.py tests/test_ledger_snapshots.py \
        tests/test_command_surface_matrix.py
    make all

Expect `make all` to end with all tests passed, lint/format/type/audit clean.
All three `.ambr` files (`test_desloppify_snapshots.ambr`,
`test_ledger_snapshots.ambr`, `test_command_surface_matrix.ambr`) show as
modified after regeneration, but the *blocks* that change differ. The desloppify
`.ambr` regenerates both blocks. The matrix `.ambr` change is confined to the
eleven `test_machine_envelope_matrix[desloppify-*]` blocks (each `findings` list
collapses to empty). The ledger `.ambr` changes **only** its
`test_clean_ledger_envelope_snapshot` block (the sole passing `sternum` finding
becomes `findings: []`); its `test_over_ration_envelope_snapshot` block is
unchanged because that block's only finding is already the failing one, which
slimming keeps.

To prove the red-green ordering, stage the test edits first and run the affected
clean-pass / matrix tests before applying the projection edit. The ledger clean
test is included because it is the genuinely red-green ledger case; the ledger
over-ration test is deliberately omitted, as it is unchanged by slimming:

    pytest tests/test_desloppify_snapshots.py::test_clean_pass_envelope_snapshot \
        tests/test_ledger_snapshots.py::test_clean_ledger_envelope_snapshot \
        tests/test_command_surface_matrix.py::test_desloppify_shape_across_phases

Expect failures on `assert result["findings"] == []` (the desloppify and ledger
clean snapshot suites) and on the changed matrix assertion before the source
edit, and passes after.

## Validation and acceptance

Acceptance is observable behaviour plus a pinned contract:

- Running `desloppify` over a slop-free manuscript emits an envelope whose
  `result.findings` is `[]`, `result.violations` is `[]`, `ok` is `true`, at
  exit 0. Running `desloppify --ledger` over a within-ration manuscript does the
  same.
- Running `desloppify --chapter N` over a chapter with exactly one over-threshold
  rule emits `result.findings` containing exactly that one finding (no passing
  rules), `result.violations` naming that rule, `ok: false`, exit 4 —
  unchanged gating, slimmed trail.
- The decision and rationale are written in the design or developers' guide and
  both projection docstrings cite it.

Quality criteria (what "done" means):

- Tests: `make test` passes; the new clean-pass `findings == []` assertions fail
  before the projection edit and pass after; all three full-trail suites
  (`test_desloppify_snapshots.py`, `test_ledger_snapshots.py`,
  `test_command_surface_matrix.py`) are green with the slimmed snapshots; the two
  new projection-level unit tests pass.
- Lint/typecheck/format/audit: `make lint`, `make typecheck`, `make check-fmt`,
  `make audit` all clean (i.e. `make all` green).
- Markdown: `make markdownlint` and `make nixie` clean on every changed `.md`.
- No change to `result.violations`, `ok`, or any exit code for any input.

Quality method (how we check): run `make all` for code commits and `make
markdownlint` + `make nixie` for markdown commits, exactly as AGENTS.md requires;
read back the clean-pass and one-hit envelopes to confirm the observable shape.

## Idempotence and recovery

Every step is re-runnable. Re-running the snapshot regeneration is safe — it
rewrites the `.ambr` from the current code, so a half-applied edit recovers by
re-running `pytest --snapshot-update` after the source edit is complete. The doc
edits are plain text edits with no side effects. If a gate fails, fix and re-run;
nothing is destructive and there is no migration or external state. If Work item
2's snapshots are regenerated *before* the source edit is finished, they capture
the wrong shape — recover by completing the source edit and regenerating again,
then re-running `make all`.

## Interfaces and dependencies

No new interface is introduced. The two functions whose behaviour changes keep
their signatures:

- `novel_ralph_skill.commands._desloppify_report.report_outcome(report:
  DetectionReport) -> CommandOutcome` — `result["findings"]` now lists only
  over-threshold findings; all other keys unchanged.
- `novel_ralph_skill.ledger.report.ledger_report_outcome(report: LedgerReport)
  -> CommandOutcome` — same slimming for the per-device trail.

Both continue to consume the unchanged detection cores
`novel_ralph_skill.rulepack.detect.detect` and
`novel_ralph_skill.ledger.detect.detect`, which still return a finding per
rule/device. The slimming lives entirely in the projection, at the envelope
boundary, consistent with ADR-003's single shared envelope contract.

No new external dependency. The e2e layer's cuprum usage
(`cuprum.ProgramCatalogue`, `cuprum.ProjectSettings`, `cuprum.program.Program`,
`cuprum.sh.make`, `SafeCmd.run_sync`, the `exit_code`/`stdout`/`stderr` result
fields — all verified against the locked source under
`/data/leynos/Projects/cuprum`) is untouched, because the e2e assertions read
`violations`/`ok`, not the slimmed trail.

## Revision note

Initial draft (2026-06-25). Decomposes roadmap 7.1.3 into a no-code consumer
inventory (WI0), a documentation decision record (WI1), the projection slimming
with snapshot conformance (WI2), and a cross-reference sweep with the full gate
(WI3). Proposes and justifies the violations-only clean-pass contract rather than
leaving the shape undecided; pins the cuprum and snapshot facts the plan relies
on against the locked sources.

Round 2 revision (2026-06-25). Resolves the round-1 logisphere review's single
blocking defect (B1: incomplete consumer inventory / suite goes red) and the
related advisory A2. What changed: (1) corrected the false "only two consumers"
premise throughout the Purpose, rationale point 3, Context, Risks, and Decision
Log — the full-trail envelope is read by **three** test consumers, the third
being `tests/test_command_surface_matrix.py::test_desloppify_shape_across_phases`
(line 717, `len(result["findings"]) == 24` across eleven clean phases) and its
snapshot `tests/__snapshots__/test_command_surface_matrix.ambr` (eleven
`test_machine_envelope_matrix[desloppify-*]` blocks, 264 `rule_id` rows). (2)
Work item 0 now runs an exhaustive `tests/` + `skill/` + `novel_ralph_skill/`
sweep (verified: `grep -rn 'findings'` over all three) and records a classified
inventory in the Decision Log; the three full-trail test sites are confirmed and
no fourth or production reader exists. (3) Work item 2 now changes the matrix
`== 24` assertion to the slimmed `findings == []` (keeping the `set(result)`
membership check), updates the matrix docstring, and regenerates the third
`.ambr` alongside the other two in the same commit. (4) The Scope Tolerance was
raised from 6 to 9 files with the eight-file edit set pre-counted, and the
Ambiguity Tolerance was re-scoped so the three known test consumers are
mechanical updates rather than escalation triggers — escalation now fires only on
a fourth full-trail consumer or a production reader. (5) Pre-resolved the ledger
over-ration `next(... device_id == "sternum")` mechanics (still resolves
post-slim) and noted the clean-pass desloppify test's `for finding in findings`
loop becomes a no-op, making the explicit `== []` assertion load-bearing. The
remaining work is unchanged in shape; the edit set is now eight files and stays
in bounds.

Round 3 revision (2026-06-25). Resolves the round-2 review's single blocking
defect (B1, Doggylump): Work item 2 step 2 misdescribed the ledger over-ration
snapshot. It claimed a "passing sibling device" that "drops out" under slimming
and instructed adding `assert len(findings) == 1` to
`test_over_ration_envelope_snapshot` to pin that drop-out. That is false: the
`_LEDGER` fixture (`tests/test_ledger_snapshots.py:35-42`) defines exactly one
device (`sternum`), confirmed against `tests/__snapshots__/
test_ledger_snapshots.ambr` (the over-ration block, lines 40-82, is a single
`passed: False` finding). Under violations-only slimming that sole finding is the
failing one, so the over-ration `findings` is unchanged — `len(findings) == 1`
holds identically before and after and is not red-green, and the over-ration
`.ambr` block does **not** regenerate. What changed: Work item 2 test edit 2 now
states the fixture is single-device, distinguishes the two ledger cases (the
**clean** block is the genuinely red-green case that regenerates to `findings:
[]`; the over-ration block is unchanged by slimming), drops the misleading
`len(findings) == 1` rationale from the over-ration test, and pins the ledger
slimming solely on `test_clean_ledger_envelope_snapshot`. The Concrete-steps
red-green ordering, the Work item 2 validation paragraph, and the Risks
"projections drift apart" mitigation were corrected to stop implying the
over-ration ledger `.ambr` regenerates and to spell out per-block which `.ambr`
blocks actually change. No work-item structure, scope, or file count changed; the
edit set remains eight files.

## Addenda

Post-merge corrections folded onto this completed task. Each runs as a
lightweight addendum pass (no plan, no design-review cycle): the change, the
gates, and a merge. They are tracked as nested sub-tasks under 7.1.3 on the
roadmap.

- 7.1.3.1 — Extend the ledger snapshot fixture to a multi-device pack
  (from review:7.1.3; low). The `_LEDGER` snapshot fixture
  (`tests/test_ledger_snapshots.py:35-42`) is single-device (`sternum`), so the
  end-to-end ledger envelope never exercises a passing sibling device dropping
  out under violations-only slimming — only the new unit test covers that drop.
  Round 3 of this plan corrected the over-ration test precisely because the
  single-device fixture cannot show the drop. Add a multi-device ledger fixture
  (one over-ration device beside an in-ration sibling) so the snapshot layer
  gets the same sibling-drop coverage the rule-pack path's one-hit snapshot
  enjoys, and regenerate the affected `.ambr` block. Test/fixture-only.

- 7.1.3.2 — Derive the desloppify/ledger exit code from the slimmed failed
  filter (from audit:7.1.3; low). In both `report_outcome`
  (`commands/_desloppify_report.py`) and `ledger_report_outcome`
  (`ledger/report.py`) the exit `code` derives from `report.passed` while
  `violations`/`findings` derive independently from the `failed` filter, leaving
  a latent path where a report whose `passed` disagrees with its findings emits
  a self-contradictory `ok: true` envelope with non-empty `violations`. Compute
  `code` from the same `failed` list (`SUCCESS` when empty else
  `ACTIONABLE_FINDING`) so the exit code and `violations` cannot diverge by
  construction, and add a unit test pinning the invariant. If the
  finding-outcome envelope-projection consolidation (phase 7 reroute) lands
  first, this derivation folds into the shared builder there. Localised
  correctness fix plus one unit test.
