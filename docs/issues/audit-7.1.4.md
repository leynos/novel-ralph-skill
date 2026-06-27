# Post-merge audit — roadmap task 7.1.4

Audit of the codebase after task 7.1.4 ("Extract the shared finding-outcome
envelope skeleton into a contract-package builder and route both projections
through it") merged to `main` at commit `9aeed7e`. The task replaced the
verbatim-identical envelope skeleton shared by the two deterministic
finding-outcome projections — `report_outcome`
(`novel_ralph_skill/commands/_desloppify_report.py`) and `ledger_report_outcome`
(`novel_ralph_skill/ledger/report.py`) — with one shared builder,
`build_finding_outcome`, added to the lowest-layer contract package
(`novel_ralph_skill/contract/finding_outcome.py`) and exported from
`novel_ralph_skill/contract/__init__.py`. The builder is generic over an opaque
finding type and takes every per-path detail as an injected callable or value
(`identify`, `payload`, `describe`, `passed`, `clean_message`, `extra_result`),
so it imports neither `rulepack` nor `ledger` and creates no import cycle. It
filters a report's findings to the failed ones, derives the exit code from that
same `failed` list (closing the latent self-contradictory-envelope path tracked
as addendum 8.1.3.2 / its 7.1.3.2 twin), and assembles `result`
(`extra_result` keys first, then `violations`, then the slimmed `findings`) and
`messages`. The change pinned the builder with a dedicated unit file
(`tests/test_finding_outcome.py`), strengthened the two call-site suites with
exit-code and `result` key-order assertions (`tests/test_desloppify_report.py`),
and recorded the seam in the developers' guide.

Trail followed: `docs/novel-ralph-harness-design.md` §3.1, §3.2, §4.4, §6.1–§6.3;
the ADRs (ADR-001 detect-only boundary, ADR-003 shared interface contract,
ADR-005 five-script surface, ADR-007 command-name source of truth);
`docs/developers-guide.md` (the "single finding-outcome envelope skeleton" and
"clean-pass findings contract" sections); `docs/issues/audit-7.1.3.md` (its
Finding 3 / proposed roadmap item on ruff `ARG`); `AGENTS.md` (quality gates,
400-line file cap, CQS, en-GB Oxford spelling); the ExecPlan artefacts
(`docs/execplans/roadmap-7-1-4.md`,
`docs/execplans/roadmap-7-1-4.review-round-2.md`); and the
`python-router`/`leta`/`sem`/`en-gb-oxendict` skills for navigation, history,
and prose. Files inspected:
`novel_ralph_skill/contract/finding_outcome.py`,
`novel_ralph_skill/contract/__init__.py`,
`novel_ralph_skill/contract/envelope.py`,
`novel_ralph_skill/commands/_desloppify_report.py`,
`novel_ralph_skill/commands/_desloppify_ledger.py`,
`novel_ralph_skill/ledger/report.py`,
`novel_ralph_skill/commands/_reconcile.py`;
`tests/test_finding_outcome.py`, `tests/test_desloppify_report.py`,
`tests/test_desloppify_e2e.py`; `pyproject.toml` (ruff `select`);
`docs/roadmap.md` §7.1.

The merged change is high quality: the builder is a small, total, generic
function placed in the correct lowest layer with no import cycle; the module and
function docstrings state the two load-bearing contracts (exit-code-from-`failed`
and `result` key-insertion order) and the no-cycle invariant; both call sites
inject only their genuine per-path detail; the new unit file pins the four
behaviours that the order-insensitive `.ambr`/`json.loads` suites cannot; and
the developers' guide records the seam and its re-use policy. The findings below
are minor: a **test gap where no test pins the rendered raw-JSON `result` key
order end-to-end** (Finding 1, the substantive one), an **ergonomic
seven-parameter signature behind a `PLR0913` suppression** (Finding 2), a
**cross-module name collision between the two `_finding_payload`/`_finding_message`
helpers** (Finding 3), and an **unrealised prior-audit roadmap proposal (ruff
`ARG`) that remains the cheapest guard for this builder's injected-callable
style** (Finding 4).

## Finding 1 — no test pins the rendered raw-JSON `result` key order end-to-end (severity: low)

**Category:** test-gap

**Location:** `tests/test_desloppify_report.py:82-96`
(`test_report_outcome_preserves_result_key_order`) and the builder twin at
`tests/test_finding_outcome.py:113-132`; the e2e oracles
`tests/test_desloppify_e2e.py:137,231,262` (and the ledger e2e) that read stdout
via `json.loads`; the renderer at
`novel_ralph_skill/contract/envelope.py:143-151` (`render_machine`).

The key-order contract for `result` is load-bearing precisely because
`render_machine` calls `json.dumps` with no `sort_keys` (envelope.py:151), so the
raw machine JSON line emits keys in dict-insertion order. The builder's
docstring and both unit suites name this and guard it — but only at the
*Python-dict* level: every assertion is of the form
`list(outcome.result) == [...]`, taken on the `CommandOutcome.result` mapping
*before* it reaches `render_machine`. The end-to-end e2e oracles, by contrast,
`json.loads` the stdout (test_desloppify_e2e.py:137, :231, :262), which discards
order. The `.ambr` snapshots that do compare rendered output use
`sort_keys=True` (per the note at `test_reconciliation_payload.py:17`), so they
too cannot catch a reorder. The chain from `result` dict to rendered line is in
fact correct — `render_machine` does `dict(env.result)` (envelope.py:148),
preserving order, then `json.dumps` without sorting — but no single test asserts
that the *bytes on stdout* for the desloppify or ledger commands carry
`pack`/`total_words`/`violations`/`findings` (or `violations`/`findings`) in
that order. A future change to `render_machine` (e.g. someone adding
`sort_keys=True` "for determinism") would pass every existing suite while
silently breaking the very contract 7.1.4 went out of its way to pin.

**Proposed fix:** Add one end-to-end raw-string assertion for a failing
desloppify (rule-pack) run that asserts the rendered stdout line contains the
`result` keys in contract order without parsing — e.g. assert the substring
`"result": {"pack"` … `"violations"` … `"findings"` ordering, or compare
`result.stdout` against an un-sorted snapshot, in `test_desloppify_e2e.py`. One
case per `extra_result` shape (the rule-pack path with extras, the ledger path
without) closes the gap. This makes the renderer-level invariant a gate failure
rather than something only the pre-render dict assertions defend, so a stray
`sort_keys` is caught at the boundary it would actually break.

## Finding 2 — `build_finding_outcome`'s seven-parameter signature sits behind a `PLR0913` suppression (severity: low)

**Category:** ergonomics

**Location:** `novel_ralph_skill/contract/finding_outcome.py:50-59`
(`build_finding_outcome`, carrying
`# noqa: PLR0913  # pylint: disable=too-many-arguments`).

The builder takes seven parameters — `findings`, `identify`, `payload`,
`describe`, `passed`, `clean_message`, `extra_result` — and suppresses the
`PLR0913` too-many-arguments warning to do so. Four of these (`identify`,
`payload`, `describe`, `passed`) are a cohesive bundle: they are the per-finding
*projection* the call site supplies, always passed together, and they share a
single opaque `Finding` type variable. The suppression is reasonable for now —
the precedent is `build_envelope`, which carries the same `# noqa: PLR0913` with
a `why:` comment because its parameters are fixed one-per-contract-field
(envelope.py:68-70). But unlike `build_envelope`, this builder's parameter set
is not fixed by the contract: the multi-pack surface (roadmap 7.1.6/7.1.7) that
this builder explicitly anticipates may add further per-path knobs, and each new
knob widens an already-suppressed signature. The `build_envelope` suppression is
paired with an explanatory `why:` comment; this builder's bare `# noqa` is not.

**Proposed fix:** Two options, in increasing effort. (a) Minimal: add a `why:`
comment beside the `# noqa: PLR0913` mirroring `build_envelope`'s, recording
that the four projection callables are a deliberate per-path bundle injected
together — so the suppression reads as a considered decision, not an oversight.
(b) If 7.1.6/7.1.7 adds further per-path parameters: group the four projection
callables into a small frozen `FindingProjection[Finding]` dataclass (the
`identify`/`payload`/`describe`/`passed` quartet), reducing the signature to
`findings`, `projection`, `clean_message`, `extra_result` and dropping the
suppression entirely. Prefer (a) now and revisit (b) when the multi-pack surface
actually lands; do not pre-emptively add the dataclass for two call sites.

## Finding 3 — the two `_finding_payload` / `_finding_message` helpers share names across modules (severity: low)

**Category:** similarity

**Location:** `novel_ralph_skill/commands/_desloppify_report.py:91,131`
(rule-pack `_finding_payload`/`_finding_message`) and
`novel_ralph_skill/ledger/report.py:38,70` (ledger
`_finding_payload`/`_finding_message`).

After 7.1.4 the two projection modules each define a private `_finding_payload`
and `_finding_message` with identical names but deliberately distinct bodies
(the per-hit payloads and prose are settled, separate contracts — 8.1.4/8.1.5
territory, as both modules' docstrings note). The name collision is harmless to
the runtime (they are module-private and injected by reference, never imported
across modules) and is arguably a feature: the parallel names signal the parallel
roles. But it is a mild readability hazard in tooling that flattens symbols —
`leta grep "_finding_payload"` returns four hits across two packages, and a
reader skimming a stack trace or a grep result must check the module path to know
*which* projection a `_finding_payload` belongs to. The shared-skeleton extraction
makes the two modules look more alike than before (both now end in a thin
`build_finding_outcome(...)` call wired to same-named helpers), sharpening the
risk of conflating them.

**Proposed fix:** This is a judgement call — flag, do not force. If disambiguation
is wanted, rename per domain: `_rule_finding_payload`/`_rule_finding_message` in
the rule-pack module and `_device_finding_payload`/`_device_finding_message` in
the ledger module, matching the `RuleFinding`/`DeviceFinding` types they project
and the `rule_id`/`device_id` slugs they emit. This costs nothing at the call
site (the helpers are passed by reference to `build_finding_outcome`) and makes
a flat symbol list self-describing. Alternatively, keep the names and accept the
parallelism as intentional; the module docstrings already state the
distinctness, so this is a minor ergonomic preference rather than a defect.

## Finding 4 — ruff `ARG` (unused-argument), proposed in audit-7.1.3, is still absent and would guard this builder's injected-callable style (severity: low)

**Category:** test-gap

**Location:** `pyproject.toml` `[tool.ruff.lint] select` (no `ARG` entry);
`docs/issues/audit-7.1.3.md` Finding 3 / proposed roadmap item 1.

Audit-7.1.3 (Finding 3 and its proposed roadmap item) recommended adding `"ARG"`
to the ruff `select` list, because the codebase's functional style — many small
projections and mutators threaded through call sites — makes refactor-orphaned
parameters a recurring risk a gate should catch cheaply. That proposal has not
been actioned: `ARG` is still absent from the (otherwise extensive) `select`
list. Task 7.1.4 makes the recommendation more, not less, relevant. The new
builder is parameterised over four injected callables, and both call sites supply
small `lambda finding: …` projections and same-shaped helper functions. This is
exactly the shape where an injected callable's parameter (or a helper's) can be
left unread after a future tweak — and exactly the case `ARG` exists to catch.
The builder also introduces a fresh `# noqa`-bearing signature (Finding 2),
adding to the population of suppressions a parameter-hygiene rule would keep
honest.

**Proposed fix:** Carry forward audit-7.1.3's proposal: add `"ARG"`
(flake8-unused-arguments) to the ruff `select` list, triaging the small number of
intentional unused arguments (interface/callback conformance) with local
`# noqa: ARG00x` plus a one-line reason or the leading-underscore convention.
This is a re-statement, not a new finding — but two consecutive §7.1 audits now
naming the same gap is itself signal that the guard is worth the one-time triage
cost. No 7.1.4 code is currently in violation; the value is forward-looking
across the multi-pack surface (7.1.6/7.1.7) the builder anticipates.

## Proposed roadmap items (proposal only — the root agent owns the roadmap)

1. **Add an end-to-end raw-JSON key-order assertion for the finding-outcome
   commands** (severity: low). Add one un-parsed stdout assertion per
   `extra_result` shape (rule-pack with `pack`/`total_words`, ledger without) to
   the desloppify/ledger e2e suites, pinning that `render_machine` emits `result`
   keys in contract order on the wire. Rationale (Finding 1): the order contract
   is currently guarded only at the pre-render dict level; a stray
   `sort_keys=True` in `render_machine` would pass every existing suite while
   breaking the contract 7.1.4 exists to protect.

2. **Enable ruff `ARG` (unused-argument) in the lint `select`** (severity: low).
   Re-statement of audit-7.1.3's proposed item, now reinforced by 7.1.4's
   injected-callable builder. Add `"ARG"` to `pyproject.toml`
   `[tool.ruff.lint] select`, triage the existing intentional unused arguments
   with local `# noqa: ARG00x` plus a reason (or the leading-underscore
   convention for interface-fixed signatures). Rationale (Finding 4): two
   consecutive §7.1 audits name the same gap; the builder's projection-callable
   style is precisely the pattern the rule guards.
