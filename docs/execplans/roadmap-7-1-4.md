# Extract the shared finding-outcome envelope skeleton into a contract-package builder

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DRAFT (round 2)

## Purpose / big picture

Roadmap task 7.1.4 removes a verbatim-identical duplication between the two
deterministic *finding-outcome* projections so that the multi-pack surface
(roadmap 8.1.6/8.1.7) and any future change to the
violations-versus-findings relationship is made in one place, not kept in
lockstep across two files by hand.

The two projections are:

- `report_outcome` in
  `novel_ralph_skill/commands/_desloppify_report.py` (the rule-pack path), and
- `ledger_report_outcome` in `novel_ralph_skill/ledger/report.py` (the
  `desloppify --ledger` device-ledger path).

After roadmap task 7.1.3 slimmed both audit trails, the two functions share an
identical *skeleton*: filter the report's findings to the failed ones; choose
the exit code; assemble a `result` mapping carrying a `violations` slug list and
a slimmed `findings` payload list; assemble `messages` as one human-prose line
per failed finding, or a single clean-pass note. They differ only in five
injectable details:

1. the per-hit `result.findings[]` payload projection
   (`_finding_payload`, distinct per path and explicitly kept distinct);
2. the id accessor that builds the `violations` slug list
   (`finding.rule_id` versus `finding.device_id`);
3. extra `result` keys the rule-pack path carries before `violations`/`findings`
   (`pack`, `total_words`); the ledger path carries none;
4. the human-prose line per failed finding (`_finding_message`, distinct per
   path);
5. the clean-pass message string (`"no slop detected"` versus
   `"no rationing breaches detected"`).

This task extracts the shared skeleton into a single *contract-package builder*
that injects those five details, and routes both projections through it. The
per-hit payload projections and the per-hit message builders stay where they
are (they are settled per-path contracts, design §4.4 and §6.3); only the
envelope *skeleton* is consolidated.

The roadmap entry also folds in addendum 8.1.3.2 (and its 7.1.3 twin, recorded
in `docs/execplans/roadmap-7-1-3.md` §Addenda as 7.1.3.2). Both `report_outcome`
and `ledger_report_outcome` today derive the exit code from `report.passed`
while `violations`/`findings` derive independently from the `failed` filter,
leaving a latent self-contradictory `ok: true` envelope with non-empty
`violations` if the two ever disagree. The roadmap entry says: "The
exit-code-from-`failed` derivation tracked as addendum 8.1.3.2 folds into this
builder if 7.1.4 lands after it; if 7.1.4 lands first, derive the code from the
same `failed` list the builder filters." Addendum 8.1.3.2 is **not yet checked**
in `docs/roadmap.md` (line 4843, `- [ ]`), and the live source still derives the
code from `report.passed` (`_desloppify_report.py:180`, `ledger/report.py:131`).
So 7.1.4 lands first, and **this builder derives the exit code from the same
`failed` list it filters**, closing 8.1.3.2/7.1.3.2 by construction.

A reader can observe the result three ways after this change. First, exactly one
function in the `contract` package owns the failed-filter, exit-code, and
`violations`/`findings`/`messages` skeleton, and both `report_outcome` and
`ledger_report_outcome` are thin call sites that inject only their five
per-path details (visible by reading the two now-short functions). Second, the
desloppify and ledger envelopes are byte-for-byte unchanged on every existing
input — every snapshot (`tests/__snapshots__/test_desloppify_snapshots.ambr`,
`tests/__snapshots__/test_ledger_snapshots.ambr`,
`tests/__snapshots__/test_command_surface_matrix.ambr`) stays green without
regeneration. Third, a new unit test pins the builder's exit-code-from-`failed`
invariant directly, so a report whose `passed` flag disagrees with its `failed`
filter can no longer emit a self-contradictory envelope.

This is a pure refactor plus one correctness tightening (the exit-code
derivation). No new command, flag, library, pack-schema field, or envelope key
is introduced, and **no observable output changes for any input the two paths
produce today** (the detection cores always set `report.passed == all(f.passed
…)`, so deriving the code from `failed` yields the identical code on every real
report; the change only removes the *latent* divergence the addendum names).

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- The shared envelope shape `{command, schema_version, ok, working_dir, result,
  messages}` (design §3.1; `docs/adr-003-shared-interface-contract.md`) must not
  change. This task touches neither `build_envelope` nor `render_machine`.
- The `result` payload shape of **each** path must be byte-for-byte unchanged
  for every existing input. Rule-pack `result` keys remain, in order, `pack`,
  `total_words`, `violations`, `findings`; ledger `result` keys remain, in
  order, `violations`, `findings`. The `render_machine` JSON serialisation does
  **not** sort keys (`novel_ralph_skill/contract/envelope.py:143-151`,
  `json.dumps(ordered)` with `dict(env.result)` and no `sort_keys`), so the
  builder must emit each path's `result` keys in that exact insertion order. The
  extra keys (`pack`, `total_words`) must precede `violations`/`findings`.
- The §3.2 exit-code contract must be preserved: a clean report exits `0`
  (`ExitCode.SUCCESS`), a report with any failed finding exits `4`
  (`ExitCode.ACTIONABLE_FINDING`). After this task the code derives from the
  `failed` list (empty → `SUCCESS`, else `ACTIONABLE_FINDING`), which equals the
  current `report.passed`-derived code for every real detection report (the
  cores guarantee `passed == not failed`); the *observable* code is unchanged.
- The slimmed clean-pass findings contract (roadmap 7.1.3; developers' guide
  "The clean-pass findings contract") must be preserved: `result.findings`
  carries only the over-threshold/over-ration findings, built from the same
  `failed` filter that feeds `violations`, so a clean pass emits `findings: []`
  and `violations: []`.
- The per-hit payload projections must stay distinct and unchanged. The
  rule-pack `_finding_payload` (`_desloppify_report.py:91-128`) and the ledger
  `_finding_payload` (`ledger/report.py:33-62`) are deliberately different (the
  ledger module docstring states it "must NOT reuse or alter the rule-pack
  `_finding_payload`"). The builder injects each as a callable; it does **not**
  merge, share, or alter them. Likewise the two `_finding_message` builders stay
  per-path.
- Layering: the builder lives in the `contract` package (the lowest layer; both
  `commands/_desloppify_report.py` and `ledger/report.py` already import *from*
  `contract`). The builder must **not** import `rulepack` or `ledger` types — it
  is generic over an opaque finding type and takes injected callables, so no
  import cycle is created (`contract/errors.py:14` records the no-cycle
  invariant the `contract` package preserves).
- No new external dependency, command, flag, or pack-schema field.
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments, and
  commits (AGENTS.md).
- Each commit passes every gate in AGENTS.md ("Change quality and committing"):
  `make check-fmt`, `make lint` (Ruff + 100% interrogate docstring coverage +
  Pylint), `make typecheck` (`ty`), `make test`, `make audit`; and for any `.md`
  change, `make markdownlint` and `make nixie`.
- No code file may exceed 400 lines (AGENTS.md). The new builder module is small
  (one function plus its docstring); both call sites *shrink*. `_desloppify.py`
  is at 389 lines but is not touched by this task.

## Tolerances (exception triggers)

- Scope: if the implementation requires changes to more than 7 files or more
  than ~250 net lines of code, stop and escalate. The expected edit set is
  pre-counted at five files and is in bounds: 1 new source file
  (`novel_ralph_skill/contract/finding_outcome.py`), 2 edited source files
  (`commands/_desloppify_report.py`, `ledger/report.py`), 1 edited
  `contract/__init__.py` (to re-export the builder, matching the package's
  existing public-surface convention), and 1 new unit-test module
  (`tests/test_finding_outcome.py`). Optionally 1 doc file
  (`docs/developers-guide.md`) if the new shared seam warrants a one-paragraph
  note; that keeps the count at six, still in bounds.
- Snapshot regeneration: if **any** of the three `.ambr` snapshots
  (`test_desloppify_snapshots.ambr`, `test_ledger_snapshots.ambr`,
  `test_command_surface_matrix.ambr`) regenerates, stop and escalate — this is a
  behaviour-preserving refactor and a snapshot diff means the result shape or
  key order drifted. The correct outcome is that `make test` passes with **no**
  `--snapshot-update` needed.
- Output drift: if the builder changes `result` (any key, value, or key order),
  `messages`, `ok`, or an exit code for **any** input the current functions
  produce, stop and escalate — that is out of contract. The exit-code-from-
  `failed` change is in contract precisely because it is observationally
  identical for every real report; if a real report is found whose `passed`
  disagrees with `not failed`, that is a detection-core bug to escalate, not a
  builder behaviour to "fix" silently.
- Layering: if making the builder generic appears to require importing a
  `rulepack` or `ledger` type into the `contract` package, stop and escalate —
  that signals the parameterisation is wrong (the builder must be generic over
  an opaque finding type via `TypeVar`).
- Per-hit payload merge: if the work appears to require sharing or unifying the
  two `_finding_payload` functions, stop and escalate — that is explicitly out
  of scope (the per-hit payloads are settled, distinct contracts; only the
  skeleton consolidates).
- Iterations: if `make all` still fails after 3 fix attempts on a single work
  item, stop and escalate.
- Ambiguity: if a non-test production consumer is found that depends on the
  exit code being derived from `report.passed` rather than from the findings
  (none is expected; the runner reads `outcome.code` only), stop and present the
  conflict.

## Risks

    - Risk: The builder accidentally reorders the `result` keys (e.g. emits
      `violations` before the rule-pack `pack`/`total_words` extras), churning
      the machine JSON output and the snapshots even though the *set* of keys is
      unchanged. `render_machine` does not sort keys, so insertion order is
      observable in the raw JSON line.
      Severity: high
      Likelihood: medium
      Mitigation: the builder takes the extra keys as an ordered mapping that it
      inserts *before* `violations` and `findings`, exactly matching the current
      literals (`{pack, total_words, violations, findings}` and `{violations,
      findings}`). **The committed key-order guard is a call-site regression
      assertion added in Work item 2**: a unit test that calls the *real*
      `report_outcome`/`ledger_report_outcome` and asserts
      `list(outcome.result) == ["pack", "total_words", "violations", "findings"]`
      and `list(outcome.result) == ["violations", "findings"]` directly on the
      returned `CommandOutcome.result` (a plain insertion-ordered `dict`). This
      catches a mis-wired `extra_result` at the actual rule-pack call site (e.g.
      `{"total_words": …, "pack": …}` in the wrong order), which the isolated
      Work-item-1 builder test cannot, because that test exercises the builder
      with synthetic `extra_result` rather than the real wiring. Note the limits
      of the other guards, so they are not relied upon for order: the `.ambr`
      snapshots sort keys (syrupy) and so survive a reorder; the cross-command
      matrix asserts only `set(result)` membership
      (`tests/test_command_surface_matrix.py:613`); and every e2e/command suite
      decodes with `json.loads(...)` and reads by key, never asserting order. The
      Work-item-1 builder unit test additionally pins the builder's insertion
      order in isolation. The Snapshot-regeneration and Output-drift Tolerances
      remain hard stops on any *value* drift.

    - Risk: Making the builder generic forces a `rulepack`/`ledger` type import
      into the `contract` package, creating an import cycle.
      Severity: medium
      Likelihood: low
      Mitigation: the builder is generic over an opaque `TypeVar` finding type
      and never names a concrete finding class; it takes the id accessor and the
      payload/message projections as injected `Callable`s, mirroring the existing
      injected-callable helpers (`commands/_reconcile.py:95`,
      `commands/_state_mutators.py:164`). The Layering Tolerance is a hard stop if
      an import proves necessary.

    - Risk: The exit-code-from-`failed` change alters observable behaviour for
      some input, turning a pure refactor into a behaviour change.
      Severity: medium
      Likelihood: low
      Mitigation: the detection cores set `report.passed = all(finding.passed …)`
      (`rulepack/detect.py`, `ledger/detect.py`), so `passed` is true exactly
      when `failed` is empty for every report the cores produce; the derived code
      is identical. The new unit test constructs a *deliberately inconsistent*
      report (a `passed=True` report carrying a failing finding) to prove the
      builder now follows `failed` — this is the only case where behaviour
      differs from the old code, and it is the latent bug the addendum closes, not
      a real-report regression. The Output-drift Tolerance guards real inputs.

    - Risk: The two `_finding_payload` projections get accidentally unified
      because they look similar at the call site.
      Severity: medium
      Likelihood: low
      Mitigation: the builder injects each path's `_finding_payload` unchanged;
      the Per-hit-payload-merge Tolerance is a hard stop. The ledger module
      docstring's existing "must NOT reuse or alter the rule-pack
      `_finding_payload`" note stays, reworded only to point at the shared
      *skeleton* builder (which does not touch the payload).

    - Risk: A future maintainer cannot tell the new builder is the single home of
      the skeleton, and re-forks it.
      Severity: low
      Likelihood: low
      Mitigation: the builder carries a docstring naming it the single
      finding-outcome skeleton, both call-site docstrings cite it, it is
      re-exported from `contract/__init__.py` (the package's documented public
      surface), and a focused unit-test module pins its contract.

## Progress

    - [x] Work item 0: Confirm the consumer inventory, the result-key-order
      facts, and the exit-code addendum status (no code change). Deliverable is
      the Decision Log entry pinning that (a) the three `.ambr` snapshots must
      stay green with no regeneration, (b) `render_machine` preserves insertion
      order, (c) 8.1.3.2/7.1.3.2 is unlanded so the builder owns the
      exit-code-from-`failed` derivation, and (d) no production consumer reads the
      exit code from `report.passed`. (DONE 2026-06-27; see Decision Log entry
      "Work item 0 inventory and fact confirmation".)
    - [x] Work item 1: Add the shared builder in
      `novel_ralph_skill/contract/finding_outcome.py`, re-export it from
      `contract/__init__.py`, and pin it with a new unit-test module
      `tests/test_finding_outcome.py` (skeleton assembly, key order,
      exit-code-from-`failed` invariant). Builder is added but not yet wired into
      the two call sites. (DONE 2026-06-27; `make all` green, no `.ambr`
      regeneration, coderabbit 0 findings. See Surprises for the PEP 695 /
      frozen-sequence deviations from the plan's recommended signature.)
    - [x] Work item 2: Route `report_outcome` and `ledger_report_outcome` through
      the builder, injecting their five per-path details; delete the duplicated
      skeleton from both. Add the **required** call-site key-order regression guard
      to `tests/test_desloppify_report.py` (`list(outcome.result)` on the real
      `report_outcome`/`ledger_report_outcome`) plus per-path exit-code
      assertions. Confirm all three `.ambr` snapshots stay green with no
      regeneration. Update both module/function docstrings to cite the shared
      builder; reword the ledger "must NOT reuse `_finding_payload`" note to point
      at the skeleton. (DONE 2026-06-27; `make all` green;
      `pytest --snapshot-update` left every `.ambr` untouched — behaviour
      byte-for-byte preserved; call-site key-order assertions
      `["pack", "total_words", "violations", "findings"]` and
      `["violations", "findings"]` pass; coderabbit 0 findings.)
    - [x] Work item 3: Cross-reference sweep and final gate — record the shared
      seam in the developers' guide if warranted, update the roadmap success
      criterion wording check, and run the complete `make all` + markdown gate.
      (DONE 2026-06-27; recorded the `build_finding_outcome` scope and re-use
      policy in the developers' guide "The clean-pass findings contract" section;
      added a "Subsumed by 7.1.4" cross-reference to the 8.1.3.2 addendum without
      flipping its checkbox; confirmed the 7.1.4 success-criterion wording matches
      what was built; `make all` + `make markdownlint` + `make nixie` all green.)

## Surprises & discoveries

    - Builder signature: the plan's recommended signature used a module-level
      `typ.TypeVar("_Finding")`, but the repo's Ruff config enforces PEP 695
      (`UP046`), so the builder is written with inline type parameters
      (`def build_finding_outcome[Finding](...)`), matching the codebase
      convention (e.g. `freeze_mapping[K, V]` in `_freeze.py`). No mechanism
      change; the builder is still generic over an opaque finding type with
      injected callables.
    - PLR0913 (too-many-arguments, 7 > 4): suppressed with
      `# noqa: PLR0913  # pylint: disable=too-many-arguments`, matching the
      established convention for the sibling injected-parameter helper
      `build_envelope` (`contract/envelope.py:68`). The keyword-only injection
      surface is deliberate.
    - `clean_message` placed *before* `extra_result=None` in the signature so
      the required keyword precedes the defaulted one (both are keyword-only
      after `*`, so order is cosmetic; this avoids a default-before-required
      ordering wart). The plan's draft listed `extra_result` first, but the
      round-2 review confirmed either order is legal under keyword-only.
    - `CommandOutcome` freezes `messages` to a tuple via `freeze_sequence` in
      `__post_init__`, so the builder unit tests assert
      `list(outcome.messages) == [...]` rather than comparing against a list
      literal directly.
    - The `_outcome` test helper takes a typed `extra_result` parameter rather
      than a `**kwargs: object` splat, because `ty` rejects splatting an
      `object`-typed mapping into the builder's typed `extra_result` parameter
      (the Ruff-style `# type: ignore[arg-type]` does not satisfy `ty`).

## Decision log

    - Decision: Work item 0 inventory and fact confirmation (no code change).
      Verified facts (implementing agent, 2026-06-27):
      (a) `report_outcome` (`commands/_desloppify_report.py:155`) is consumed only
      by `commands/_desloppify.py` (import line 44, call line 273) and the tests
      (`tests/test_desloppify_report.py`); `ledger_report_outcome`
      (`ledger/report.py:107`) is consumed only by
      `commands/_desloppify_ledger.py` (import line 40, call line 97) and the tests
      (`tests/test_desloppify_report.py`). No other in-package caller exists, so
      the rewrite touches no further call site (`leta refs`).
      (b) `render_machine` (`contract/envelope.py:126-151`) ends with
      `json.dumps(ordered)` and carries **no** `sort_keys`, so `result` insertion
      order is preserved verbatim in the raw machine JSON line. `CommandOutcome`
      freezes `result` via `freeze_mapping` (`_freeze.py:27-29`), which wraps
      `dict(mapping)` in a `MappingProxyType` — insertion order is preserved, so
      `list(outcome.result)` reflects the builder's insertion order.
      (c) The runner reads the exit code from `outcome.code`
      (`contract/runner.py:182`, `:250` `sys.exit(outcome.code)`), never from
      `report.passed`, so the exit-code-from-`failed` derivation change cannot
      affect the runner.
      (d) Addendum 8.1.3.2 is unchecked (`docs/roadmap.md:4843`, `- [ ]`) and the
      live source still derives the code from `report.passed`
      (`_desloppify_report.py` and `ledger/report.py`, confirmed by reading both
      `report_outcome`/`ledger_report_outcome` bodies). So 7.1.4 lands first and
      **this builder owns the exit-code-from-`failed` derivation**, closing
      8.1.3.2/7.1.3.2 by construction.
      (e) The two skeletons are verbatim-identical bar the five injectable details
      (per-hit payload, id accessor, extra result keys, per-hit message,
      clean-pass message), confirming the refactor is a pure extraction.
      Rationale: makes the refactor provably behaviour-preserving and pins the
      builder's ownership of the exit-code derivation before any code change.
      Date/Author: 2026-06-27, implementing agent.

    - Decision: The shared builder lives in the `contract` package
      (`novel_ralph_skill/contract/finding_outcome.py`) and is generic over an
      opaque finding type.
      Rationale: `contract` is the lowest layer and already owns `CommandOutcome`
      and `ExitCode`; both `commands/_desloppify_report.py` and
      `ledger/report.py` already import from it, so placing the builder there lets
      both consume it with no new cross-package coupling and no import cycle
      (`contract/errors.py:14` records the no-cycle invariant). Making it generic
      over a `TypeVar` finding type with injected callables keeps `contract` free
      of any `rulepack`/`ledger` import.
      Date/Author: 2026-06-27, planning agent.

    - Decision: The builder derives the exit code from the `failed` list it
      filters (empty → `SUCCESS`, else `ACTIONABLE_FINDING`), not from
      `report.passed`.
      Rationale: roadmap 7.1.4 states the exit-code-from-`failed` derivation
      (addendum 8.1.3.2, twin 7.1.3.2) "folds into this builder if 7.1.4 lands
      after it; if 7.1.4 lands first, derive the code from the same `failed` list
      the builder filters." Addendum 8.1.3.2 is unchecked in `docs/roadmap.md`
      (line 4843) and the live source still derives from `report.passed`
      (`_desloppify_report.py:180`, `ledger/report.py:131`), so 7.1.4 lands first
      and owns the derivation. This is observationally identical for every real
      report (the cores guarantee `passed == not failed`) and closes the latent
      self-contradictory-envelope path by construction.
      Date/Author: 2026-06-27, planning agent.

    - Decision: The builder accepts the extra `result` keys as an ordered mapping
      inserted *before* `violations`/`findings`, so each path's `result` key order
      is byte-for-byte preserved.
      Rationale: `render_machine` (`contract/envelope.py:126-151`) calls
      `json.dumps(ordered)` with `dict(env.result)` and **no** `sort_keys`, so the
      raw machine JSON preserves `result` insertion order. The rule-pack path
      emits `pack, total_words, violations, findings`; the ledger path emits
      `violations, findings`. Preserving order keeps the raw machine JSON line
      byte-for-byte unchanged. **The key-order claim is guarded by a committed
      call-site regression test added in Work item 2**, not by the existing
      suites: syrupy sorts dict keys, so the `.ambr` snapshots survive a reorder;
      the cross-command matrix asserts only `set(result)` membership; and every
      e2e/command suite decodes the envelope with `json.loads(...)` and reads by
      key, never asserting key order. So **no existing test guards the wired call
      sites' `result` key order** — the new Work-item-2 assertion (`list(
      outcome.result)` on the real `report_outcome`/`ledger_report_outcome`)
      closes that gap, and the Work-item-1 builder test pins the builder's
      insertion order in isolation.
      Date/Author: 2026-06-27, planning agent.

    - Decision: The per-hit `_finding_payload` and `_finding_message` functions
      stay per-path and are injected unchanged; only the envelope *skeleton*
      consolidates.
      Rationale: roadmap 7.1.4 success criterion: the builder injects "only their
      per-hit payload, id accessor, extra result keys, and clean-pass message;
      the per-hit payload projection is unchanged". The ledger payload is
      deliberately distinct from the rule-pack payload (ledger module docstring),
      and 8.1.4/8.1.5 own the per-hit field contract. Merging payloads is out of
      scope.
      Date/Author: 2026-06-27, planning agent.

    - Decision: No external-library behaviour is load-bearing for this task; no
      firecrawl/cuprum verification is required for the change itself.
      Rationale: this task edits two pure projection functions and adds one pure
      builder, all in-process Python operating on already-built dataclasses and
      returning a `CommandOutcome`. It invokes no subprocess and touches neither
      cuprum, Cyclopts argument parsing, `pytest-timeout`, `pytest-xdist`, nor
      `uv` resolution. The only runtime behaviours it relies on — `CommandOutcome`
      construction (`contract/runner.py:126-147`), envelope rendering via
      `render_machine`, and syrupy snapshot capture — are already exercised by the
      green suites this task inherits. The e2e layer (which *does* use cuprum) is
      untouched because the observable envelope output is byte-for-byte preserved
      (see the `roadmap-7-1-3.md` cuprum-pinning note, verified against the locked
      source under `/data/leynos/Projects/cuprum`; this task adds no cuprum call).
      Date/Author: 2026-06-27, planning agent.

## Outcomes & retrospective

Completed 2026-06-27. Measured against the Purpose:

- One function — `build_finding_outcome`
  (`novel_ralph_skill/contract/finding_outcome.py`) — owns the failed-filter,
  exit-code, and `violations`/`findings`/`messages` skeleton; both
  `report_outcome` (`commands/_desloppify_report.py`) and `ledger_report_outcome`
  (`ledger/report.py`) are now thin call sites injecting only their five per-path
  details.
- The per-hit `_finding_payload`/`_finding_message` projections are untouched and
  stay per-path; the builder injects each unchanged and never merges them.
- The §3.2 exit-code contract and the slimmed clean-pass findings contract are
  preserved: `make all` is green and `pytest --snapshot-update` over all three
  `.ambr` suites leaves every snapshot byte-for-byte unchanged, proving no
  observable `result`/`messages`/`ok`/exit-code drift on any current input.
- The exit code now derives from the `failed` filter the builder projects, so the
  latent self-contradictory-envelope path (roadmap addendum 8.1.3.2 / its 7.1.3.2
  twin) is closed by construction. 8.1.3.2 is annotated "Subsumed by 7.1.4" in
  `docs/roadmap.md` (checkbox left for the workflow). The closure is pinned by
  `tests/test_finding_outcome.py` (the deliberately-inconsistent input case) and
  by the per-path exit-code assertions in `tests/test_desloppify_report.py`.
- The load-bearing `result` key-order fact — unguarded by the key-sorting `.ambr`
  snapshots and the read-by-key command suites — is now guarded by call-site
  assertions in `tests/test_desloppify_report.py`
  (`list(outcome.result) == ["pack", "total_words", "violations", "findings"]`
  and `["violations", "findings"]`) and pinned in isolation by
  `tests/test_finding_outcome.py`.
- The new shared seam's scope and re-use policy is recorded in
  `docs/developers-guide.md` under "The clean-pass findings contract".

Scope held: five source/doc files plus one test module touched (builder,
`contract/__init__.py`, two call sites, the projection test, the developers'
guide, the roadmap cross-reference, and the new builder test) — within the
five-to-six-file tolerance. No external-library claim was load-bearing, so no
firecrawl/cuprum verification was required. Three deviations from the plan's
recommended signature are logged in Surprises & discoveries (PEP 695 inline type
params, the PLR0913 suppression, and the frozen-`messages`/typed-`extra_result`
test adjustments); none changed the mechanism or the observable contract.

## Context and orientation

Assume no prior knowledge of this repository. The relevant pieces:

- The harness invokes five deterministic console-scripts every turn and gates on
  their output. They share one JSON envelope `{command, schema_version, ok,
  working_dir, result, messages}` (design §3.1;
  `docs/adr-003-shared-interface-contract.md`). The harness reads `result` and
  `ok`; it never parses `messages`. The five exit codes are 0 success, 1 benign
  negative, 2 usage error, 3 state/input error, 4 actionable finding (design
  §3.2; ADR-003 Table 2).
- A command body returns a `CommandOutcome` (a frozen dataclass:
  `code: ExitCode`, `result: Mapping[str, object]`, `messages: Sequence[str]`;
  `novel_ralph_skill/contract/runner.py:126-147`) and the shared `run` wrapper
  builds and emits the envelope from it (`runner.py:169-250`). `run` exits with
  `outcome.code`; it reads the code from the returned `CommandOutcome`, never
  from `report.passed` (so deriving the code differently inside the projection
  cannot affect the runner).
- The machine rendering preserves `result` key insertion order.
  `render_machine` (`novel_ralph_skill/contract/envelope.py:126-151`) builds an
  ordered dict `{command, schema_version, ok, working_dir, result, messages}`
  and calls `json.dumps(ordered)` with `dict(env.result)` and **no**
  `sort_keys`, so whatever order the projection inserts `result` keys is the
  order in the emitted JSON line.
- `desloppify` (the rule-pack path) reads a versioned TOML rule pack and reports
  prose-slop hits without editing or judging (design §4.4, §6.1, §6.2). Its
  detection core `novel_ralph_skill/rulepack/detect.py` defines `RuleFinding`
  (`rule_id`, `pattern`, `count`, `threshold`, `basis`, `density`, `passed`,
  `lines`) and `DetectionReport` (`pack`, `total_words`, `findings`, `passed`,
  where `passed == all(f.passed …)`). Its projection `report_outcome` in
  `novel_ralph_skill/commands/_desloppify_report.py:155-197` turns a
  `DetectionReport` into a `CommandOutcome`. Today it:
  - computes `failed = [f for f in report.findings if not f.passed]`;
  - sets `code = SUCCESS if report.passed else ACTIONABLE_FINDING`;
  - sets `result = {"pack": …, "total_words": …, "violations": [f.rule_id for f
    in failed], "findings": [_finding_payload(f) for f in failed]}`;
  - sets `messages = [_finding_message(f) for f in failed] or ["no slop
    detected"]`.
- `desloppify --ledger` (the device-ledger path, design §6.3) reads a per-novel
  `device-ledger.toml` and enforces rationing. Its detection core
  `novel_ralph_skill/ledger/detect.py` defines `DeviceFinding` (`device_id`,
  `pattern`, `count`, `ration_kind`, `max_count`, `bound`, `offending_chapters`,
  `passed`, `lines`) and `LedgerReport` (`findings`, `passed`). Its projection
  `ledger_report_outcome` in `novel_ralph_skill/ledger/report.py:107-145` turns
  a `LedgerReport` into a `CommandOutcome`. Today it:
  - computes the same `failed` filter;
  - sets `code = SUCCESS if report.passed else ACTIONABLE_FINDING`;
  - sets `result = {"violations": [f.device_id for f in failed], "findings":
    [_finding_payload(f) for f in failed]}` (no `pack`/`total_words` extras);
  - sets `messages = [_finding_message(f) for f in failed] or ["no rationing
    breaches detected"]`.
- The two skeletons are verbatim-identical except for the five injectable
  details enumerated in the Purpose. The per-hit `_finding_payload`
  (`_desloppify_report.py:91-128` and `ledger/report.py:33-62`) and
  `_finding_message` (`_desloppify_report.py:131-152` and `ledger/report.py:65
  -104`) builders are deliberately distinct and stay per-path.
- The result shape is regression-guarded by snapshot suites plus paired semantic
  assertions:
  - `tests/test_desloppify_snapshots.py` with
    `tests/__snapshots__/test_desloppify_snapshots.ambr` (clean pass: `result =
    {findings: [], pack: offenders, total_words: 18, violations: []}`; one hit:
    the single `smirked` finding).
  - `tests/test_ledger_snapshots.py` with
    `tests/__snapshots__/test_ledger_snapshots.ambr` (clean ledger: `result =
    {findings: [], violations: []}`; over-ration: the single `sternum` finding).
  - `tests/test_command_surface_matrix.py` (line 613:
    `assert set(result) == {"pack", "total_words", "violations", "findings"}`;
    plus the eleven `test_machine_envelope_matrix[desloppify-*]` blocks in
    `tests/__snapshots__/test_command_surface_matrix.ambr`).
  - `tests/test_desloppify_report.py` (projection-level slimming unit tests for
    both paths, added by roadmap 7.1.3).
  - `tests/test_desloppify_finding_message.py` (per-hit message unit tests).
- Because syrupy serialises dict snapshots with sorted keys, the `.ambr` files do
  **not** by themselves catch a `result` key reorder. **Nor does any existing
  end-to-end or command suite catch it**: every test that reads the envelope
  decodes it with `json.loads(...)` into a `dict` and then asserts on individual
  keys (`tests/test_command_surface_matrix.py:239`, `:332`, `:418`;
  `tests/test_desloppify_command.py:48`; `tests/test_ai_isms_e2e.py:243`).
  Although a Python `dict` produced by `json.loads` does preserve the JSON's
  insertion order, **no existing assertion ever inspects that order** — they read
  by key (`envelope["result"]`, `result["violations"]`) or compare the membership
  set (`set(result)`), both of which are order-insensitive. The verified facts:
  the `tests/__snapshots__/test_desloppify_snapshots.ambr` snapshot emits the
  rule-pack `result` keys as `findings, pack, total_words, violations`
  (alphabetical, not insertion order — confirmed in the live `.ambr`), and the
  cross-command matrix asserts only `set(result) == {…}`
  (`tests/test_command_surface_matrix.py:613`). **Net effect: today no committed
  test guards the `result` key order of the wired call sites `report_outcome`/
  `ledger_report_outcome`.** This plan therefore adds a *call-site* key-order
  regression guard in Work item 2 — asserting `list(outcome.result)` directly on
  the `CommandOutcome` each real projection returns — and pins the builder's
  insertion order in isolation in Work item 1. All three `.ambr` files must still
  stay green with **no** regeneration, because the result *values* are unchanged,
  but the load-bearing key-order guard is the new call-site assertion, not the
  snapshots.

Terms of art, defined:

- *Finding-outcome envelope skeleton*: the shared shape of
  `report_outcome`/`ledger_report_outcome` — filter to failed findings, choose
  the exit code, assemble `result` (`violations` + slimmed `findings` + any extra
  keys) and `messages` (one line per failed finding, or a clean-pass note).
- *Per-hit payload projection* (`_finding_payload`): the pure function mapping
  one finding to its `result.findings[]` dict. Distinct per path; not in scope to
  merge.
- *Id accessor*: the callable extracting a finding's slug for the `violations`
  list (`f.rule_id` versus `f.device_id`).
- *Extra result keys*: the path-specific keys preceding `violations`/`findings`
  in `result` (`pack`, `total_words` for the rule-pack path; none for the
  ledger).
- *Clean-pass message*: the single human line a finding-free scan emits
  (`"no slop detected"` versus `"no rationing breaches detected"`).

### External-library and cuprum pinning

No locked external library's behaviour is load-bearing for this task, and this
plan makes **no** new behavioural claim about cuprum, Cyclopts, `pytest-timeout`,
`pytest-xdist`, or `uv` that would need firecrawl verification. The change edits
two pure projection functions and adds one pure builder, all operating on
in-memory dataclasses and returning a `CommandOutcome`; it invokes no subprocess.
The e2e layer that *does* drive the installed console-script through cuprum
(`/data/leynos/Projects/cuprum`; the surface — `cuprum.ProgramCatalogue`,
`cuprum.ProjectSettings`, `cuprum.program.Program`, `cuprum.sh.make`,
`SafeCmd.run_sync` and its `exit_code`/`stdout`/`stderr` fields — was verified
against the locked source and documented in `docs/execplans/roadmap-7-1-3.md`)
is untouched: the observable envelope output is byte-for-byte preserved, so no
e2e fixture or cuprum call changes. If implementation finds an e2e or console
test whose expected output would change, that is an Output-drift Tolerance breach
to escalate, not a fixture edit to improvise.

## Plan of work

The work proceeds in four ordered, independently committable items. Work item 0
is a no-code confirmation gate; Work item 1 adds and pins the builder; Work item
2 routes both call sites through it; Work item 3 sweeps cross-references and runs
the full gate. The builder is added *before* it is wired (test-first: its unit
tests are red until the builder exists, green after), and the call-site rewrite
is proven by the **unchanged** snapshots.

### Work item 0 — Confirm the inventory, the key-order facts, and the addendum status

No code change. The purpose is to make the refactor provably behaviour-preserving
and to confirm the builder owns the exit-code-from-`failed` derivation.

Implements: roadmap 7.1.4 (the exit-code derivation "folds into this builder …
if 7.1.4 lands first"); design §3.1 (`result` is machine-actionable data), §3.2
(exit codes), §4.4 (`desloppify`), §6.1-§6.3 (rule-pack and device-ledger packs);
ADR-003.

Steps:

1. Confirm with `leta refs` that `report_outcome` is consumed only by
   `commands/_desloppify.py`/`_desloppify_report.py` and the tests
   (`test_desloppify_report.py`, snapshots), and `ledger_report_outcome` only by
   `commands/_desloppify_ledger.py` and the tests. Confirm the runner reads the
   exit code from the returned `CommandOutcome.code`, never from `report.passed`,
   so the derivation change cannot affect the runner
   (`leta show run` / read `contract/runner.py:241-250`).
2. Confirm `render_machine` does not sort `result` keys
   (`contract/envelope.py:126-151`) and record the exact current `result`
   key-order for each path (rule-pack: `pack, total_words, violations,
   findings`; ledger: `violations, findings`).
3. Confirm addendum 8.1.3.2 is unchecked in `docs/roadmap.md` (line ~4843,
   `- [ ]`) and that the live source still derives the code from `report.passed`
   (`_desloppify_report.py:180`, `ledger/report.py:131`), establishing that
   7.1.4 lands first and owns the derivation.
4. Record the classified inventory and the three facts (key order preserved,
   runner reads `CommandOutcome.code`, addendum unlanded) in the Decision Log.

Docs to read: design §3.1, §3.2, §4.4, §6.1-§6.3; ADR-003 (the envelope and
exit-code contract); developers' guide "The clean-pass findings contract".

Skills to load: `leta` (refs/show for the consumer inventory and the runner read
path); `grepai` (semantic sweep for any consumer of the exit code). No code skill
needed (no code change).

Tests: none (no code change). Deliverable is the Decision Log entry.

Validation: this item commits only the updated ExecPlan. Run `make markdownlint`
and `make nixie` over the changed `.md`. Running `make all` is harmless and
confirms a clean baseline.

### Work item 1 — Add the shared builder and pin it with a unit test

Add the builder in `novel_ralph_skill/contract/finding_outcome.py`, re-export it
from `contract/__init__.py`, and pin it with `tests/test_finding_outcome.py`. The
builder is added but **not yet** wired into the two call sites, so this item is
self-contained and gate-passable on its own (the builder is exercised by its unit
tests; the call sites still use their inline skeletons).

Implements: roadmap 7.1.4 ("one shared contract-package builder owns the
failed-filter, exit-code, and `violations`/`findings`/`messages` skeleton");
design §3.1, §3.2; ADR-003 (the shared envelope and exit-code contract the
builder centralises).

Source edits:

1. Create `novel_ralph_skill/contract/finding_outcome.py` defining a single
   builder. The recommended signature (generic over an opaque finding type, no
   `rulepack`/`ledger` import) is, in `contract/finding_outcome.py`:

       from __future__ import annotations

       import typing as typ

       from novel_ralph_skill.contract.exit_codes import ExitCode
       from novel_ralph_skill.contract.runner import CommandOutcome

       if typ.TYPE_CHECKING:
           import collections.abc as cabc

       _Finding = typ.TypeVar("_Finding")


       def build_finding_outcome(
           findings: cabc.Sequence[_Finding],
           *,
           identify: cabc.Callable[[_Finding], str],
           payload: cabc.Callable[[_Finding], cabc.Mapping[str, object]],
           describe: cabc.Callable[[_Finding], str],
           passed: cabc.Callable[[_Finding], bool],
           extra_result: cabc.Mapping[str, object] | None = None,
           clean_message: str,
       ) -> CommandOutcome:
           ...

   The body:
   - computes `failed = [f for f in findings if not passed(f)]`;
   - derives `code = ExitCode.SUCCESS if not failed else
     ExitCode.ACTIONABLE_FINDING` (the exit-code-from-`failed` derivation,
     closing 8.1.3.2/7.1.3.2);
   - builds `result` by inserting the `extra_result` keys first (in their given
     order), then `violations` (`[identify(f) for f in failed]`), then `findings`
     (`[payload(f) for f in failed]`), so each path's key order is preserved;
   - builds `messages = [describe(f) for f in failed] or [clean_message]`;
   - returns `CommandOutcome(code=code, result=result, messages=messages)`.

   Use an explicit empty-mapping default for `extra_result` (e.g. a default of
   `None` coalesced to `{}` inside the body, or an immutable empty mapping) so the
   ledger path can omit it; follow the `python-types-and-apis` guidance on
   defaulting an injected mapping parameter. Give the function a full NumPy-style
   docstring (interrogate enforces 100% coverage) naming it the single
   finding-outcome skeleton, citing design §3.1/§3.2 and ADR-003, and explaining
   the key-order and exit-code-from-`failed` contracts.
2. Re-export `build_finding_outcome` from `novel_ralph_skill/contract/__init__.py`
   (add it to the import block and the module docstring's public-surface list),
   matching the package's existing convention that the shared contract surface is
   re-exported there.

Test edits:

1. Create `tests/test_finding_outcome.py` with unit tests over a tiny local
   dummy finding type (a small frozen dataclass with an id, a `passed` flag, and
   a payload field — no `rulepack`/`ledger` import, proving the builder is
   generic):
   - *Slimming + skeleton*: a mix of passing and failing findings yields
     `result["violations"]` and `result["findings"]` containing exactly the
     failing ids/payloads, and `messages` one `describe` line per failed finding.
   - *Clean pass*: all-passing findings yield `violations == []`, `findings ==
     []`, `code == ExitCode.SUCCESS`, and `messages == [clean_message]`.
   - *Exit-code-from-`failed` invariant* (the 8.1.3.2/7.1.3.2 closure): a
     deliberately inconsistent input — a failing finding present — yields
     `code == ExitCode.ACTIONABLE_FINDING` regardless of any external "passed"
     signal, because the builder reads only the `failed` filter. (This is the
     case the old `report.passed`-derived code could get wrong; assert the
     builder is correct by construction.)
   - *Extra-result key order*: a call with `extra_result={"pack": "p",
     "total_words": 3}` yields `list(result) == ["pack", "total_words",
     "violations", "findings"]`; a call with no `extra_result` yields
     `list(result) == ["violations", "findings"]`. This pins the load-bearing
     insertion order the raw-JSON output depends on (the snapshots cannot, because
     syrupy sorts keys).

Docs to read: design §3.1 (envelope, `result`), §3.2 (exit codes); ADR-003;
`python-types-and-apis` (the generic builder signature: `TypeVar`, injected
`Callable`s, defaulting an injected mapping parameter); `python-data-shapes` (the
`result` mapping assembly and ordered-key preservation); `python-testing` (unit
test layout in the top-level `tests/` tree).

Skills to load: `python-router`, then `python-types-and-apis` (the builder is a
typed generic API surface) and `python-testing`. Optionally `arch-crate-design`
is **not** needed (single Python package). No property or mutation tooling is
warranted: the builder is a deterministic filter-and-assemble with an enumerable
boundary (clean / one-failed / mixed), which AGENTS.md covers with unit tests; if
the exit-code-from-`failed` invariant later looks worth a property over arbitrary
pass/fail vectors, reconsider `hypothesis` via `python-verification`, but the
four enumerated unit cases fully pin the contract here.

Tests: the new `tests/test_finding_outcome.py` (four cases above). They are red
until the builder exists and green after, within this single commit.

Validation: `make all` (`make check-fmt`, `make lint` including interrogate
docstring coverage, `make typecheck`, `make test`, `make audit`) green. No `.ambr`
regeneration occurs (no call site changed yet).

### Work item 2 — Route both projections through the builder

Rewrite `report_outcome` and `ledger_report_outcome` to call
`build_finding_outcome`, injecting their five per-path details, and delete the
now-duplicated inline skeleton from both. The proof of behaviour-preservation is
that **every** existing snapshot stays green with no regeneration.

Implements: roadmap 7.1.4 ("both `report_outcome` and `ledger_report_outcome`
consume it, injecting only their per-hit payload, id accessor, extra result keys,
and clean-pass message; the per-hit payload projection is unchanged; the §3.2
exit-code contract and the slimmed clean-pass findings contract are preserved");
design §4.4, §6.1-§6.3.

Source edits (both in one commit, so the two paths cannot drift):

1. `novel_ralph_skill/commands/_desloppify_report.py`, `report_outcome`
   (lines 155-197): replace the inline body with a single
   `build_finding_outcome` call:

       return build_finding_outcome(
           report.findings,
           identify=lambda finding: finding.rule_id,
           payload=_finding_payload,
           describe=_finding_message,
           passed=lambda finding: finding.passed,
           extra_result={"pack": report.pack, "total_words": report.total_words},
           clean_message="no slop detected",
       )

   The `extra_result` mapping is inserted before `violations`/`findings`, so the
   key order `pack, total_words, violations, findings` is preserved. Keep
   `_finding_payload` and `_finding_message` unchanged. Update the function and
   module docstrings to state the skeleton now comes from
   `contract.finding_outcome.build_finding_outcome` and that the exit code derives
   from the failed filter (citing the design §3.2 exit-code contract).
2. `novel_ralph_skill/ledger/report.py`, `ledger_report_outcome`
   (lines 107-145): the same rewrite, with the ledger's id accessor
   (`finding.device_id`), its `_finding_payload`/`_finding_message`, no
   `extra_result`, and `clean_message="no rationing breaches detected"`:

       return build_finding_outcome(
           report.findings,
           identify=lambda finding: finding.device_id,
           payload=_finding_payload,
           describe=_finding_message,
           passed=lambda finding: finding.passed,
           clean_message="no rationing breaches detected",
       )

   Keep the ledger `_finding_payload`/`_finding_message` unchanged. Update the
   module docstring: reword the existing "must NOT reuse or alter the rule-pack
   `_finding_payload`" note so it still asserts the per-hit payload is distinct,
   but clarifies that the shared *skeleton* (the `build_finding_outcome` builder)
   is consumed by both paths — the builder injects each payload and never merges
   them.

Detection cores (`rulepack/detect.py`, `ledger/detect.py`) and the per-hit
`_finding_payload`/`_finding_message` functions are **not** touched.

Test edits:

1. Behaviour-preservation of result *values* needs no new test logic: the
   existing
   `tests/test_desloppify_report.py` (projection slimming), the two snapshot
   suites, the cross-command matrix, and `tests/test_desloppify_finding_message.py`
   all continue to pass against the rewritten call sites with **no** snapshot
   regeneration. Confirm this explicitly:
   - run `make test` and verify green;
   - run `pytest --snapshot-update tests/test_desloppify_snapshots.py
     tests/test_ledger_snapshots.py tests/test_command_surface_matrix.py` and
     verify `git status` shows **no** change to any `.ambr` file (a changed
     `.ambr` is a Snapshot-regeneration Tolerance breach — stop and escalate).
2. **Required — call-site key-order regression guard.** Extend
   `tests/test_desloppify_report.py` with two assertions that call the *real*
   wired projections and pin the `result` key order directly on the returned
   `CommandOutcome.result` (a plain insertion-ordered `dict`):

       # rule-pack call site
       outcome = report_outcome(report_with_one_hit)
       assert list(outcome.result) == ["pack", "total_words", "violations", "findings"]

       # ledger call site
       outcome = ledger_report_outcome(ledger_report_with_one_hit)
       assert list(outcome.result) == ["violations", "findings"]

   These are the load-bearing guard against a mis-wired `extra_result` at the
   actual call site (e.g. `{"total_words": …, "pack": …}` in the wrong order),
   which the isolated Work-item-1 builder test cannot catch because it exercises
   the builder with synthetic `extra_result` rather than the real wiring.
   `tests/test_desloppify_report.py` already constructs one-hit reports for both
   paths (`_rule_finding`/`_device_finding` helpers,
   `test_report_outcome_slims_findings_to_over_threshold` and
   `test_ledger_report_outcome_slims_findings_to_over_ration`), so reuse those
   shapes; add the `list(outcome.result)` assertion to those tests or add two
   focused `test_*_result_key_order` tests beside them. These assert order on the
   exact `dict` that `render_machine` serialises with no `sort_keys`, so they pin
   the raw-JSON key order without depending on `json.loads` round-tripping.
3. **Required — call-site exit-code assertion.** Extend
   `tests/test_desloppify_report.py` with one assertion per path that the
   rewritten projection still derives the exit code correctly from the findings
   (clean → `ExitCode.SUCCESS`, with-failure → `ExitCode.ACTIONABLE_FINDING`), so
   the per-path call sites — not only the generic builder — are pinned to the
   §3.2 exit-code contract. This is a small addition to the existing module, not
   a new module.

Docs to read: design §4.4, §6.1-§6.3; developers' guide "Rule packs and the
loader boundary", "The device ledger and per-novel rationing", and "The
clean-pass findings contract"; AGENTS.md "Refactoring heuristics" (separate the
functional refactor into its own atomic commit) and "Python verification and
testing"; `python-testing` for snapshot discipline.

Skills to load: `python-router`, then `python-abstractions` (the call sites now
inject behaviour via callables into a shared builder — a behaviour-shaped
parameterisation) and `python-testing` (confirming snapshots do not regenerate).
`leta` to confirm the two call sites have no other in-package callers that would
need updating.

Tests: the existing suites are the value-regression guard (they pass with no
`.ambr` change); **the two required additions to `tests/test_desloppify_report.py`
— the call-site key-order assertions (`list(outcome.result) == [...]` for both
paths) and the per-path exit-code assertions — are the new acceptance criteria**.
These must be present and green; the key-order assertion in particular is what
guards against a mis-wired `extra_result` shipping unguarded.

Validation: `make all` green (including the two new call-site assertions); then
the no-regeneration check (`pytest --snapshot-update …` leaves `.ambr` files
untouched). Acceptance for this item explicitly includes `list(outcome.result)`
returning `["pack", "total_words", "violations", "findings"]` for the rule-pack
projection and `["violations", "findings"]` for the ledger projection. Commit the
two source rewrites and the required test additions together so the two paths
land through the builder in one atomic, fully guarded change.

### Work item 3 — Cross-reference sweep and final gate

Record the new shared seam where the docs describe the projection layer, confirm
the roadmap success-criterion wording matches what was built, and run the
complete gate including markdown lint and nixie.

Implements: roadmap 7.1.4 success criterion; AGENTS.md "Documentation
maintenance" (proactively update affected docs; record a new abstraction's scope
and re-use policy) and "Abstraction / port / helper policy" (record the new
helper's intended scope and re-use policy in the developers' guide).

Steps:

1. Per AGENTS.md "Abstraction / port / helper policy", record the new
   `build_finding_outcome` helper's scope and re-use policy in
   `docs/developers-guide.md` (a short paragraph near the rule-pack / ledger
   projection prose, e.g. the "Rule packs and the loader boundary" or
   "The clean-pass findings contract" neighbourhood): it is the single
   finding-outcome envelope skeleton, lives in the `contract` package, is generic
   over an opaque finding type, injects each path's per-hit payload / id accessor
   / extra result keys / clean-pass message, and derives the exit code from the
   failed filter. Cross-reference design §3.1/§3.2 and ADR-003.
2. Sweep the developers' guide and design for any prose that describes the two
   projections as independently assembling the `violations`/`findings`/`messages`
   skeleton, and reword to note the shared builder; leave prose describing a
   *finding's fields* (8.1.4/8.1.5 territory) and the per-hit payload distinctness
   untouched.
3. Confirm the roadmap 7.1.4 success criterion wording in `docs/roadmap.md` still
   matches what was built; the workflow owns flipping the checkbox at merge, so
   do not edit the checkbox here. Note in Outcomes that 8.1.3.2/7.1.3.2 is closed
   by the builder's exit-code-from-`failed` derivation (the implementer may add
   a one-line cross-reference on the 8.1.3.2 roadmap entry noting it is subsumed
   by 7.1.4, if the workflow's roadmap-edit policy permits; otherwise record the
   closure in Outcomes only).
4. Run the complete gate: `make all`, then `make markdownlint` and `make nixie`
   over every changed `.md`. All must pass.

Docs to read: `docs/developers-guide.md` (rule-pack and ledger sections, "The
clean-pass findings contract"); `docs/novel-ralph-harness-design.md` §3.1, §3.2,
§4.4, §6; `docs/roadmap.md` 7.1.4 and 8.1.3.2 entries;
`docs/documentation-style-guide.md`.

Skills to load: `en-gb-oxendict` (Oxford spelling in new prose); `leta`/`grepai`
(find stale projection descriptions).

Tests: none new; the suites from Work items 1 and 2 are the regression guard.

Validation: `make all` green; `make markdownlint` and `make nixie` green on all
`.md` changes. Update `Progress` and `Outcomes & retrospective`.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-1-4`.

Work item 0 (inventory):

    leta refs report_outcome
    leta refs ledger_report_outcome
    leta show run
    grepai search --workspace Projects --project novel-ralph-skill \
        "command outcome exit code from report passed" --toon --compact
    grep -n 'sort_keys\|json.dumps' novel_ralph_skill/contract/envelope.py
    grep -n '8.1.3.2' docs/roadmap.md

Expect: `report_outcome` consumed by `_desloppify.py` and the desloppify tests;
`ledger_report_outcome` by `_desloppify_ledger.py` and the ledger tests; `run`
reads `outcome.code` (not `report.passed`); `render_machine` calls `json.dumps`
without `sort_keys`; addendum 8.1.3.2 is `- [ ]` (unlanded). Record in the
Decision Log.

Work item 1 (builder + unit test):

    # after creating contract/finding_outcome.py, editing contract/__init__.py,
    # and adding tests/test_finding_outcome.py:
    make all

Expect `make all` green; the four `tests/test_finding_outcome.py` cases pass; no
`.ambr` file changes.

Work item 2 (route both call sites):

    # after rewriting report_outcome and ledger_report_outcome AND adding the
    # required call-site key-order + exit-code assertions to
    # tests/test_desloppify_report.py:
    make all
    pytest tests/test_desloppify_report.py -q
    pytest --snapshot-update \
        tests/test_desloppify_snapshots.py tests/test_ledger_snapshots.py \
        tests/test_command_surface_matrix.py
    git status --short

Expect `make all` green; the call-site key-order assertions
(`list(outcome.result) == ["pack", "total_words", "violations", "findings"]` and
`["violations", "findings"]`) pass; and `git status` shows **no** modified
`.ambr` file after `--snapshot-update` (values are byte-for-byte preserved). A
modified `.ambr` is a Tolerance breach — stop and escalate.

Work item 3 (docs sweep + final gate):

    make all
    make markdownlint
    make nixie

Expect all three green on the changed files.

## Validation and acceptance

Acceptance is observable behaviour plus a consolidated skeleton:

- Exactly one function (`build_finding_outcome` in
  `novel_ralph_skill/contract/finding_outcome.py`) owns the failed-filter,
  exit-code, and `violations`/`findings`/`messages` skeleton; both
  `report_outcome` and `ledger_report_outcome` are thin call sites that inject
  only their five per-path details.
- Running `desloppify` over a slop-free manuscript still emits `result.findings
  == []`, `result.violations == []`, `result.pack`, `result.total_words`,
  `ok: true`, exit 0, with `result` keys in the order `pack, total_words,
  violations, findings`. Running `desloppify --chapter N` over a chapter with one
  over-threshold rule still emits exactly that one finding, that rule in
  `violations`, `ok: false`, exit 4. Running `desloppify --ledger` over a
  within-ration and an over-ration manuscript behaves identically to before.
- The exit code now derives from the `failed` filter; a report whose `passed`
  flag disagrees with its findings can no longer emit a self-contradictory
  envelope (8.1.3.2/7.1.3.2 closed), proven by `tests/test_finding_outcome.py`.
- A committed call-site key-order regression test
  (`tests/test_desloppify_report.py`) asserts `list(outcome.result) == ["pack",
  "total_words", "violations", "findings"]` on the real `report_outcome` and
  `list(outcome.result) == ["violations", "findings"]` on the real
  `ledger_report_outcome`, so a mis-wired `extra_result` at either call site
  fails the suite rather than shipping unguarded. This guard is necessary because
  the `.ambr` snapshots sort keys and every e2e/command suite decodes with
  `json.loads(...)` and reads by key, so none of them guards `result` key order.

Quality criteria (what "done" means):

- Tests: `make test` passes; the new `tests/test_finding_outcome.py` cases pass;
  the **required** call-site key-order and exit-code assertions added to
  `tests/test_desloppify_report.py` (Work item 2) pass; every existing desloppify
  and ledger suite (the two snapshot suites, the cross-command matrix, the
  projection and message unit tests) is green with **no** `.ambr` regeneration.
- Lint/typecheck/format/audit: `make lint` (Ruff + 100% interrogate docstring
  coverage + Pylint), `make typecheck` (`ty`), `make check-fmt`, `make audit` all
  clean (i.e. `make all` green).
- Markdown: `make markdownlint` and `make nixie` clean on every changed `.md`.
- No change to `result` (keys, values, or key order), `messages`, `ok`, or any
  exit code for any input the two paths produce today.

Quality method (how we check): run `make all` for code commits and `make
markdownlint` + `make nixie` for markdown commits, exactly as AGENTS.md requires;
confirm no `.ambr` regenerates via `pytest --snapshot-update … && git status`;
read back the clean-pass and one-hit envelopes to confirm the observable shape and
key order.

## Idempotence and recovery

Every step is re-runnable. The builder addition (Work item 1) is purely additive
— deleting `contract/finding_outcome.py` and its test restores the prior tree.
The call-site rewrite (Work item 2) is a behaviour-preserving edit; if a snapshot
unexpectedly regenerates, do **not** commit the regenerated `.ambr` — revert it,
diff the emitted `result` against the snapshot to find the drift (most likely a
key-order mismatch in `extra_result` insertion), fix the builder, and re-run.
The doc edits are plain-text with no side effects. Nothing is destructive and
there is no migration or external state; if a gate fails, fix and re-run.

## Interfaces and dependencies

One new interface is introduced in the `contract` package:

- `novel_ralph_skill.contract.finding_outcome.build_finding_outcome(findings,
  *, identify, payload, describe, passed, extra_result=…, clean_message) ->
  CommandOutcome` — the single finding-outcome envelope skeleton, generic over an
  opaque finding type, deriving the exit code from the `failed` filter and
  assembling `result` with `extra_result` keys first, then `violations`, then
  `findings`. Re-exported from `novel_ralph_skill.contract`.

The two existing projection functions keep their public signatures and module
locations:

- `novel_ralph_skill.commands._desloppify_report.report_outcome(report:
  DetectionReport) -> CommandOutcome` — now a thin `build_finding_outcome` call;
  `result` shape and values unchanged.
- `novel_ralph_skill.ledger.report.ledger_report_outcome(report: LedgerReport)
  -> CommandOutcome` — likewise.

The per-hit `_finding_payload` and `_finding_message` functions in both modules
are unchanged and continue to be injected into the builder. The detection cores
`novel_ralph_skill.rulepack.detect` and `novel_ralph_skill.ledger.detect` are
untouched. No new external dependency; the e2e layer's cuprum usage is untouched
because the observable envelope output is byte-for-byte preserved.

## Revision note

Initial draft (2026-06-27, round 1). Decomposes roadmap 7.1.4 into a no-code
inventory/fact-confirmation gate (WI0), the additive shared builder plus its unit
tests (WI1), the behaviour-preserving routing of both projections through the
builder proven by unchanged snapshots (WI2), and a docs sweep with the full gate
(WI3). Commits the builder to the `contract` package, generic over an opaque
finding type to avoid an import cycle (verified: `contract` is the lowest layer
and both call sites already import from it). Pins the load-bearing
`result`-key-order fact against `render_machine`'s `json.dumps` without
`sort_keys` (`contract/envelope.py:126-151`) and notes syrupy's key-sorting means
the order must be pinned by a builder unit test, not only by snapshots. Resolves
the exit-code-from-`failed` fork explicitly: addendum 8.1.3.2 (twin 7.1.3.2) is
unchecked in `docs/roadmap.md` and the live source still derives from
`report.passed`, so 7.1.4 lands first and the builder owns the derivation, closing
the addendum by construction. Records that no external-library (cuprum, Cyclopts,
pytest-timeout, pytest-xdist, uv) behaviour is load-bearing — this is in-process
pure-Python refactoring — so no firecrawl verification is required for the change.

Round 2 (2026-06-27). Resolves the design reviewer's sole blocking point — a
false validation claim plus an unguarded key-order regression. Round 1 asserted
the raw machine JSON key order was "exercised by the console-script e2e suites"
and that the raw JSON "would not survive a reorder"; this was verified false
against source. Every test that reads the envelope decodes it with
`json.loads(...)` into a `dict` and asserts by key
(`tests/test_command_surface_matrix.py:239`/`:332`/`:418`,
`tests/test_desloppify_command.py:48`, `tests/test_ai_isms_e2e.py:243`), never on
key order; the `.ambr` snapshots serialise with sorted keys (the rule-pack
`result` keys appear as `findings, pack, total_words, violations` alphabetically
in `tests/__snapshots__/test_desloppify_snapshots.ambr`); and the cross-command
matrix asserts only `set(result)` membership
(`tests/test_command_surface_matrix.py:613`). Net: no committed test guarded the
`result` key order of the wired call sites. This round (a) corrects the false
claim wherever it appeared — Context (formerly lines ~414-418), Risk #1
mitigation, and the Decision Log key-order entry — to state plainly that the
existing suites do not guard key order and why; and (b) promotes a real call-site
key-order regression guard to a **required** test and a stated acceptance
criterion in Work item 2: `tests/test_desloppify_report.py` now asserts
`list(outcome.result) == ["pack", "total_words", "violations", "findings"]` on the
real `report_outcome` and `["violations", "findings"]` on the real
`ledger_report_outcome`, so a mis-wired `extra_result` (e.g. `{"total_words": …,
"pack": …}`) at the rule-pack call site fails the suite rather than shipping
unguarded. The assertion reads `outcome.result` (the exact insertion-ordered
`dict` that `render_machine` serialises with no `sort_keys`), so it pins the
raw-JSON order without relying on `json.loads` round-tripping. The Work-item-1
isolated builder test still pins the builder's order, but is no longer claimed as
the call-site guard. No mechanism or scope change otherwise; the edit set grows
only by assertions inside the already-planned `tests/test_desloppify_report.py`
change in Work item 2 (still within the five-to-six-file Scope tolerance).
