# Post-merge audit — roadmap task 7.1.3

Audit of the codebase after task 7.1.3 ("Slim the desloppify clean-pass findings
trail") merged to `main` at commit `641e46c`. The task narrowed the envelope
projection in both `novel_ralph_skill/commands/_desloppify_report.py` and
`novel_ralph_skill/ledger/report.py` so that `result.findings` carries only the
over-threshold (rule-pack) or over-ration (ledger) entries: a clean pass now
emits `findings: []` rather than serialising every rule or device at count zero.
The detection core still aggregates a finding for every rule/device; only the
projection slims. The change regenerated the command-surface, desloppify, and
ledger snapshots, added projection-level unit coverage in
`tests/test_desloppify_report.py`, and documented the contract in the
developers' and users' guides.

Trail followed: `docs/novel-ralph-harness-design.md` §3.1, §3.3, §4.4, §6.2,
§6.3; `docs/developers-guide.md` §"The clean-pass findings contract (roadmap
task 7.1.3)" and §"The device ledger and per-novel rationing";
`docs/users-guide.md` §`desloppify` exit-code table; the ADRs (ADR-001
detect-only boundary, ADR-003 shared envelope contract, ADR-005 five-script
surface); `AGENTS.md` (quality gates, 400-line file cap, CQS, en-GB Oxford
spelling); the `python-router`/`leta`/`sem` and `en-gb-oxendict` skills for
navigation, history, and prose. Files inspected:
`novel_ralph_skill/commands/_desloppify_report.py`,
`novel_ralph_skill/commands/_wordcount_report.py`,
`novel_ralph_skill/ledger/report.py`,
`novel_ralph_skill/rulepack/detect.py`, `novel_ralph_skill/ledger/detect.py`,
`novel_ralph_skill/contract/runner.py`;
`tests/test_desloppify_report.py`, `tests/test_desloppify_snapshots.py`,
`tests/test_ledger_snapshots.py`, and the regenerated snapshot `.ambr` files;
`docs/roadmap.md` §7.25 and §7.26.

The merged change is high quality: the slimming is a one-line filter swap in each
projection, the rationale is documented as an authoritative contract in the
developers' guide with both guides cross-referencing it, the unit tests pin the
slimming directly below the snapshot suites, and the snapshot churn is a net
deletion (the payload no longer grows linearly with pack size). The findings
below are minor: a **near-duplicate envelope-projection skeleton** the change
intensified (Finding 1, the substantive one), a **latent consistency coupling**
between the exit code and the slimmed `violations`/`findings` (Finding 2), a
**unit test gap on the projected exit code** (Finding 3), and a **stale
forward-reference** in the ledger module docstring (Finding 4).

## Finding 1 — `report_outcome` and `ledger_report_outcome` are now near-identical skeletons (severity: medium)

**Category:** duplication

**Location:** `novel_ralph_skill/commands/_desloppify_report.py:155-197`
(`report_outcome`) and `novel_ralph_skill/ledger/report.py:107-145`
(`ledger_report_outcome`).

Both functions now share a verbatim skeleton:

```python
failed = [finding for finding in report.findings if not finding.passed]
code = ExitCode.SUCCESS if report.passed else ExitCode.ACTIONABLE_FINDING
return CommandOutcome(
    code=code,
    result={
        ...,
        "violations": [<id> for finding in failed],
        "findings": [_finding_payload(finding) for finding in failed],
    },
    messages=[_finding_message(finding) for finding in failed]
    or [<clean-pass note>],
)
```

They differ in exactly four particulars: the per-hit `_finding_payload`, the
id attribute name (`rule_id` vs `device_id`), the extra `result` keys the
rule-pack path adds (`pack`, `total_words`), and the clean-pass message string
(`"no slop detected"` vs `"no rationing breaches detected"`). Before 7.1.3 the
two `findings` projections diverged (one slimmed to `failed`, the ledger emitted
the full trail), which partly masked the similarity; the slimming made the
skeletons identical, so a future change to the gating/projection shape (for
instance the multi-pack surface at roadmap 7.1.6/7.1.7, or any change to how
`violations` relate to `findings`) must now be made in two places and kept in
lockstep by hand. The third sibling, `_wordcount_report.py:report_outcome`, is
genuinely different (always `SUCCESS`, no violations) and is *not* part of this
duplication.

Note the explicit ExecPlan constraint preserved in
`novel_ralph_skill/ledger/report.py:7-13`: the ledger must NOT reuse or alter the
rule-pack `_finding_payload` (per-hit payload decisions 7.1.4/7.1.5 are still
open). Any fix must therefore extract the **skeleton**, not the per-hit
payload — the payload function stays a per-package injection point.

**Proposed fix:** Extract a shared finding-outcome builder into the contract
package — e.g. `contract/runner.py` or a small `contract/projection.py` — with a
signature like
`finding_outcome(*, report, id_of, payload_of, extra_result, clean_message)`
that owns the `failed` filter, the `code` ternary, and the
`violations`/`findings`/`messages` assembly. Each call site passes its
`id_of`/`payload_of` callables, its `extra_result` dict, and its clean-pass
string. This collapses the skeleton to one home while leaving each package's
per-hit payload and operator messages untouched. This is distinct from roadmap
§7.25 (which consolidates the *loader/scan* primitives, explicitly not the
projection) and from §7.26 (the reconciliation payload), so it warrants its own
deferred lane (see proposed roadmap items below).

## Finding 2 — exit code and slimmed `violations`/`findings` are derived from two independent sources (severity: low)

**Category:** cqs

**Location:** `novel_ralph_skill/commands/_desloppify_report.py:179-186` and
`novel_ralph_skill/ledger/report.py:130-135`.

The `code` is derived from the stored `report.passed` flag, while `violations`
and the slimmed `findings` are derived independently from the
`failed = [f for f in report.findings if not f.passed]` filter. The
`DetectionReport.passed` and `LedgerReport.passed` docstrings declare the
invariant "True iff every finding passed", and the production constructors honour
it (`detect.py:277` and `:279` set `passed=all(finding.passed for finding in
findings)`). But nothing in the projection enforces the invariant: a report
whose `passed=True` disagrees with a failing finding — constructible by hand, as
the new tests do, or by a future detector that sets `passed` separately — would
emit `code=SUCCESS` (`ok: true`, exit 0) alongside a non-empty `violations`
list, a self-contradictory envelope the harness would mis-gate on. This is a
latent coupling rather than a live bug, because every production path computes
`passed` from the findings.

**Proposed fix:** Derive `passed`/`code` from the same `failed` filter inside the
projection — `code = ExitCode.SUCCESS if not failed else
ExitCode.ACTIONABLE_FINDING` — so the exit code and the violations cannot
diverge by construction, and drop the reliance on the separately-stored
`report.passed` in the projection. (Folds naturally into the Finding 1
extraction, where the shared builder would own this single derivation.)
Alternatively, if `report.passed` must remain authoritative, add an assertion or
a typed invariant at construction so the two cannot drift.

## Finding 3 — projection-level tests assert findings/violations but not the exit code (severity: low)

**Category:** test-gap

**Location:** `tests/test_desloppify_report.py:43-131`.

The four new projection tests assert `result["findings"]` and
`result["violations"]`, but none asserts `outcome.code`. The exit-code mapping is
covered end-to-end by the snapshot suites (`test_desloppify_snapshots.py:105`,
`:142`), but the pure projection — the unit the new file deliberately pins "below
the snapshot suites" — never asserts that a clean report projects
`ExitCode.SUCCESS` and a failing report projects `ExitCode.ACTIONABLE_FINDING`.
Combined with Finding 2, this means the very divergence Finding 2 describes
(code disagreeing with violations) is unenforced at the only layer that could
cheaply enforce it.

**Proposed fix:** Add `assert outcome.code == ExitCode.SUCCESS` to the two
clean-pass tests and `assert outcome.code == ExitCode.ACTIONABLE_FINDING` to the
two over-threshold/over-ration tests. If Finding 2's fix derives `code` from
`failed`, add one test that hand-builds a report with `passed=True` but a failing
finding and asserts the projection treats it as a finding (or rejects it),
pinning the invariant directly.

## Finding 4 — ledger `report.py` module docstring references a now-resolved decision and a stale "WI5 snapshot" seam (severity: low)

**Category:** docs-gap

**Location:** `novel_ralph_skill/ledger/report.py:6-13`.

The module docstring was updated for 7.1.3 (it now records the slimming) but the
surrounding framing still reads as forward-looking against decisions this commit
settled. The phrasing "it must NOT reuse or alter the rule-pack
`_finding_payload` (ExecPlan Constraint: do not pre-empt the per-hit
payload-contract decisions 7.1.4/7.1.5)" is correct and load-bearing, but the
prior 7.1.2 docstring's "the round-1 review notes 7.1.3's clean-pass slimming may
later revisit this, and the WI5 snapshot is the churn-absorbing seam" was
replaced only partially: the "WI5 snapshot … churn-absorbing seam" rationale no
longer appears, yet the developers' guide and the function docstrings are now the
authoritative home for the contract. A reader of the module docstring alone does
not learn that the §7.25 loader-consolidation lane is the place where the two
packages' shared structure is tracked, nor that the Finding 1 projection
skeleton is *not* in §7.25's scope.

**Proposed fix:** Tighten the module docstring to (a) keep the 7.1.4/7.1.5
per-hit constraint, (b) state plainly that the clean-pass slimming is now settled
and authoritative in the developers' guide "The clean-pass findings contract",
and (c) if Finding 1 is accepted, cross-reference the projection-skeleton lane so
the next reader knows the duplication is tracked rather than accidental. Mirror
the same cross-reference in `_desloppify_report.py`'s module docstring.

## Proposed roadmap items (proposal only — the root agent owns the roadmap)

1. **Single-home the finding-outcome envelope projection** (severity: medium).
   Extract the shared `failed`-filter / `code`-ternary /
   `violations`-`findings`-`messages` skeleton from `report_outcome`
   (`_desloppify_report.py`) and `ledger_report_outcome` (`ledger/report.py`)
   into one builder in the `contract` package, injecting each package's per-hit
   payload, id accessor, extra `result` keys, and clean-pass message. Distinct
   from §7.25 (loader/scan primitives, explicitly not the projection) and §7.26
   (reconciliation payload). Rationale: 7.1.3 made the two projection skeletons
   verbatim-identical, so the multi-pack surface (7.1.6/7.1.7) and any future
   change to the violations↔findings relationship must otherwise be kept in
   lockstep across two files by hand.

2. **Derive the desloppify/ledger exit code from the slimmed `failed` filter**
   (severity: low). Make the projection compute `code` from the same `failed`
   list that feeds `violations`/`findings`, removing the latent path where
   `report.passed` could disagree with a non-empty `violations` list and emit a
   self-contradictory `ok: true` envelope. Folds into item 1 if accepted; add a
   unit test pinning the invariant either way.
