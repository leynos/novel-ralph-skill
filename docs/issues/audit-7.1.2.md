# Post-merge audit — roadmap task 7.1.2

Audit of the codebase after task 7.1.2 ("Implement per-novel
`device-ledger.toml` enforcement") merged to `main` at commit `d6d5f78`. The
task added a new `novel_ralph_skill/ledger/` package (schema, validating loader,
field coercion, chapter-aware detector, envelope projection), wired
`desloppify --ledger PATH` onto whole-manuscript rationing, and shipped unit,
example, Hypothesis property, and snapshot tests plus an end-to-end check that
the loader travels in the installed wheel. The design's open question Q3 is
resolved and both guides document the device ledger.

Trail followed: `docs/novel-ralph-harness-design.md` §6.3 (resolves Q3),
`docs/developers-guide.md` §"The device ledger and per-novel rationing",
`docs/users-guide.md` §`desloppify`,
`skill/novel-ralph/references/desloppify-checklist.md`, the ADRs (ADR-001
detect-only boundary, ADR-003 shared envelope, ADR-005 five-script surface),
`AGENTS.md` (quality gates, 400-line file cap, CQS, en-GB Oxford spelling), the
`python-router` and `en-gb-oxendict` skills, and `leta`/`sem` for navigation and
history. Files inspected: `novel_ralph_skill/ledger/parse.py`, `_coerce.py`,
`_fields.py`, `detect.py`, `report.py`, `schema.py`, `errors.py`, `__init__.py`;
`novel_ralph_skill/commands/_desloppify.py` and `_desloppify_ledger.py`; the
rule-pack counterparts `novel_ralph_skill/rulepack/parse.py`, `_coerce.py`,
`detect.py`; and the tests `tests/test_ledger_command.py`,
`test_ledger_detect.py`, `test_ledger_properties.py`, `test_ledger_snapshots.py`
plus `tests/__snapshots__/test_ledger_snapshots.ambr`.

The merged change is high quality: the loader is a clean validating boundary,
the detector is pure and trivially unit-testable, the constraint-combination
semantics are precise and well documented, and the developers' guide even
pre-records the "must appear" floor as a future enhancement so the negative-only
window reading is explicit rather than accidental. The findings below are about
the **untested envelope projection** (Finding 1, the substantive one), the
**structural duplication** the new package introduces against the rule-pack
package (Findings 2 and 3), a **broken commit gate inherited and shifted** by
this merge (Finding 4), some **dead defensive code** (Finding 5), and a couple
of smaller coverage and consistency observations.

## Finding 1 — the ledger envelope projection is wholly untested except for `max_count` (severity: high)

**Category:** test-gap

**Location:** `novel_ralph_skill/ledger/report.py` (`ledger_report_outcome`,
`_finding_message`, `_finding_payload`); coverage is only indirect via
`tests/test_ledger_command.py` and `tests/__snapshots__/test_ledger_snapshots.ambr`.

**Description:** No test imports `novel_ralph_skill.ledger.report` directly. The
module is exercised only through the two command snapshots
(`test_clean_ledger_envelope_snapshot`, `test_over_ration_envelope_snapshot`),
and both fixtures use a bare `max_count` device. Consequently the three
window-breach prose branches of `_finding_message` are **never executed by any
test**:

- `allowed_chapters` → `"used in chapter(s) … outside allowed {…}"`
- `retired_after_chapter` → `"used in chapter(s) … after retirement chapter N"`
- `reserved_for_chapter` → `"used in chapter(s) … outside reserved chapter N"`

The combined breach (a device that overspends `max_count` *and* leaks outside
its window, where both clauses are joined with `"; "`) is likewise untested.
`test_ledger_detect.py` covers `offending_chapters` at the *detector* level, but
it asserts the detector's data (`finding.offending_chapters == (2, 5)`), not the
projected human prose or the `result.findings`/`violations` payload that the
window kinds produce. By contrast, the rule-pack path has a dedicated
`tests/test_desloppify_finding_message.py` pinning both of *its* message
branches; the ledger has no equivalent, even though its message function has more
branches. A regression in any window-breach message or in the window-aware
payload would ship green.

**Proposed fix:** Add a `tests/test_ledger_report.py` (mirroring
`test_desloppify_finding_message.py`) that calls `ledger_report_outcome` /
`_finding_message` directly over a `LedgerReport` constructed for each ration
kind — an `allowed_chapters` breach, a `retired_after_chapter` breach, a
`reserved_for_chapter` breach, and a paired `max_count`+window breach — and pins
the exact prose and the `result` payload (`ration_kind`, `bound`,
`offending_chapters`). Additionally, add at least one window-breach snapshot
fixture (e.g. a `retired_after_chapter` device used after retirement) to
`test_ledger_snapshots.ambr` so the end-to-end envelope for a non-`max_count`
kind is pinned. This closes the gap and makes Finding 5's dead branch visible.

## Finding 2 — `ledger/_coerce.py` is a near-verbatim copy of `rulepack/_coerce.py` (severity: medium)

**Category:** duplication

**Location:** `novel_ralph_skill/ledger/_coerce.py` (whole module) versus
`novel_ralph_skill/rulepack/_coerce.py` (whole module).

**Description:** The two `_coerce` modules are byte-for-byte identical save for
the raised error type (`LedgerError` versus `RulePackError`), the noun in the
message prefix (`"device"`/`"device ledger"` versus `"rule"`/`"rule pack"`), and
the keyword argument name (`device_id` versus `rule_id`). `_where`,
`_reject_unknown_keys`, `_require`, `_require_str`, and `_require_int` share
their entire control flow, message structure, and `bool`-rejection logic. The
ledger module's own docstring acknowledges the copy and explains why *direct
reuse* was rejected: importing the rule-pack helpers would raise the wrong typed
error, and refactoring the rule-pack loader to take an error factory would edit
a frozen module (an ExecPlan tolerance trip). That reasoning is sound for those
two options, but it does not consider the third: **extract a shared generic
helper that neither loader has to be edited destructively to adopt** — a
coercion primitive parameterised on an error-raising callback, with each package
keeping a thin error-typed wrapper. Every future TOML-backed pack (the design
hints at more under §6/§7) will otherwise add a fourth copy of this body.

**Proposed fix:** Lift the coercion primitives into one shared module (e.g.
`novel_ralph_skill/_toml_coerce.py` or a `contract`-adjacent location) that takes
an injected `raise_error(msg, *, entity_id)` callback (or an error class plus a
`where` formatter). `rulepack/_coerce.py` and `ledger/_coerce.py` each shrink to
a few lines that bind their own `RulePackError`/`LedgerError` and noun, preserving
the exact wording and typed channel the commands route on. Because the wrappers
keep the existing public-to-package names and messages, the rule-pack path stays
behaviourally byte-for-byte unchanged (satisfying the tolerance the docstring
cites) while the shared logic lives once. Gate on the existing rulepack and
ledger property suites to prove no message drift. Coordinate with roadmap §7.1
payload work, which already touches these modules.

## Finding 3 — the ledger loader and detector duplicate the rule-pack structure beyond `_coerce` (severity: medium)

**Category:** similarity

**Location:** `novel_ralph_skill/ledger/parse.py` `_entries`, `_compile_pattern`,
`_reject_duplicate_ids`, `load_ledger` versus the same-named functions in
`novel_ralph_skill/rulepack/parse.py`; and `novel_ralph_skill/ledger/detect.py`
`_scan_device` versus `novel_ralph_skill/rulepack/detect.py` `_scan_rule`.

**Description:** Beyond `_coerce`, the loader and detector carry a second layer
of structural duplication:

- `_entries` (array-of-tables guard, empty-array guard, per-entry mapping guard)
  is identical bar the noun and error type.
- `_compile_pattern` is identical bar the noun and error type.
- `_reject_duplicate_ids` is identical bar the element type and error type.
- `load_ledger`/`load_rulepack` share the whole `tomllib`-open/`OSError`/
  `TOMLDecodeError` → file-error body verbatim, differing only in the message
  noun and the `*FileError` type.
- `_scan_device` and `_scan_rule` are **byte-identical** apart from the loop
  variable name (`device`/`rule`); both split each chapter into physical lines
  and `finditer` per line into `LineHit`s.

The ledger already imports `LineHit` and `ScannedChapter` from `rulepack.detect`
(good — the hit type is shared), so the per-line scan logic is the obvious next
thing to share. Each duplicated body is a place a future fix (e.g. a newline or
overlap correction to the scan, or a change to the file-fault classification)
must be made twice and can silently diverge.

**Proposed fix:** Extract the package-agnostic primitives once. For the scan,
promote `_scan_device`/`_scan_rule` to a single `scan_pattern(compiled,
chapters) -> tuple[int, tuple[LineHit, ...]]` in `rulepack/detect.py` (or a
shared detect-core module) and have both detectors call it. For the loader,
fold `_entries`, `_compile_pattern`, `_reject_duplicate_ids`, and the
file-open/decode body into the same shared module proposed in Finding 2,
parameterised on the error factory, so the rule-pack and ledger loaders both
delegate. Keep each package's public names and messages so the typed channels
and snapshots are unchanged; gate on both property suites. This and Finding 2 are
best done as one consolidation pass.

## Finding 4 — `make markdownlint` fails on the integration branch (severity: medium)

**Category:** inconsistency

**Location:** `docs/developers-guide.md:1105-1106` (MD012/no-multiple-blanks: two
consecutive blank lines before the new "### The device ledger and per-novel
rationing" heading).

**Description:** Running `make markdownlint` — an AGENTS.md commit gate — on a
clean `d6d5f78` checkout reports one error:
`docs/developers-guide.md:1106 MD012/no-multiple-blanks`. This is the *same*
defect the 7.1.1 post-merge audit recorded as its Finding 7 (then at line 700),
which was never remediated; the 7.1.2 merge inserted the new device-ledger
subsection immediately after the offending double blank, shifting it to line 1106
and carrying the red baseline forward. A failing gate on `main` means every
subsequent task starts from a non-green lint state and may inherit or mask the
breakage. (The audit file added by this step is excluded from the attribution:
the error reproduces with this file stashed.)

**Proposed fix:** Delete the duplicate blank line at
`docs/developers-guide.md:1105-1106` so a single blank separates the preceding
paragraph from the new heading. This is a one-line fix outwith this docs-only
audit's no-edit scope, so it is recorded rather than applied; fold it into the
next task that touches the document, or take it as a trivial standalone fix. The
recurrence (now two consecutive audits) suggests the commit gate is not being run
against the full document on the implementing branch — see the proposed roadmap
item.

## Finding 5 — unreachable `"?"` fallbacks in `_finding_message` (severity: low)

**Category:** complexity

**Location:** `novel_ralph_skill/ledger/report.py:92` and `:97`
(`finding.bound[0] if finding.bound else "?"`).

**Description:** In `_finding_message`, the `retired_after_chapter` and
`reserved_for_chapter` branches guard `finding.bound[0]` with an `else "?"`
fallback, and the `allowed_chapters` branch uses `finding.bound or ()`. But the
detector's `_window` (`detect.py`) always sets `bound` to a non-empty tuple for
every window kind — `allowed_chapters` carries the allowed tuple,
`retired_after_chapter`/`reserved_for_chapter` carry `(N,)` — and only the bare
`max_count` kind has `bound is None`, which these branches never reach (they are
gated on `finding.offending_chapters`, which a `max_count`-only device never
populates). The `"?"` and `or ()` fallbacks are therefore dead defensive code:
they cannot execute given the detector's invariant, and they quietly weaken the
contract by implying `bound` might be absent where the type and the producer say
it is not.

**Proposed fix:** Either remove the fallbacks and index `finding.bound[0]`
directly (the detector's invariant guarantees it is present), adding a brief
comment that `bound` is non-empty for every window kind; or, if the defence is
wanted, replace the silent `"?"` with an assertion that makes the invariant
explicit and fails loudly in a test rather than emitting a `"?"` into user prose.
Pair this with the Finding 1 window-breach tests so whichever path is chosen is
actually exercised.

## Finding 6 — the ledger mode has no behavioural (`.feature`) coverage (severity: low)

**Category:** test-gap

**Location:** `tests/features/` (no `device_ledger.feature`);
`tests/test_ledger_command.py` (example-based command tests only).

**Description:** The rule-pack `desloppify` path and most commands carry
`pytest-bdd` `.feature` scenarios (`tests/features/*.feature`) that pin
behaviour in Given/When/Then prose. The device-ledger mode — a new user-facing
capability with several distinct outcomes (within ration, `max_count` breach,
each window breach, the `--ledger` + `--chapter` rejection, the recompute-from-
disk drop) — has only Python example tests and snapshots, no behavioural feature.
The command tests are thorough on exit codes but do not express the operator-
visible behaviour in the project's BDD idiom, leaving the ledger's behaviour
documented less consistently than the rest of the surface.

**Proposed fix:** Add a `tests/features/device_ledger.feature` with scenarios for
the within-ration pass, the `max_count` breach naming the device, at least one
window breach, the recompute-from-disk drop, and the `--ledger` + `--chapter`
usage rejection, with step bindings reusing the existing baseline-tree fixtures.
This brings the ledger to BDD parity with the rest of the command surface and
gives Finding 1's window-breach prose a behavioural home.

## Finding 7 — `load_ledger`'s `Traversable` parameter is wider than its sole caller (severity: low)

**Category:** ergonomics

**Location:** `novel_ralph_skill/ledger/parse.py` `load_ledger(path: Traversable)`;
sole caller `novel_ralph_skill/commands/_desloppify_ledger.py` `ledger_scan`
(passes a `pathlib.Path`).

**Description:** `load_ledger` types its `path` as
`importlib.resources.abc.Traversable`, and the docstring states this is purely
"for signature symmetry with `load_rulepack`", noting the device ledger is always
a filesystem `pathlib.Path` (never a packaged resource, since it is per-novel user
data with no resolver). The symmetry is cosmetic: the rule-pack loader genuinely
needs `Traversable` because it resolves a packaged resource, whereas the ledger
never does. Widening the parameter to an abstract protocol that no caller uses
trades a small loss of precision (a `Path`-only caller cannot rely on
`Path`-specific affordances) for an analogy. It is a minor ergonomic smell, not
a defect.

**Proposed fix:** Narrow `load_ledger`'s parameter to `pathlib.Path`, matching
its only caller and the design's "per-novel filesystem path" framing, and drop
the "signature symmetry" justification from the docstring. If a packaged default
ledger is ever shipped (it is not in v1 and the design says it never will be),
widen it back then. This is a judgement call; if the maintainers prefer the
parallel signatures across the two loaders, leave it and the finding stands as
documentation of the trade-off.

## Proposed roadmap item

Adding to the roadmap is reserved to the root agent; this is a proposal only.

- **Consolidate the rule-pack and device-ledger TOML-loading and scan
  primitives.** Findings 2 and 3 show `_coerce`, `_entries`, `_compile_pattern`,
  `_reject_duplicate_ids`, the `load_*` file-fault body, and the per-line
  `_scan_*` are duplicated across the two packages. A dedicated consolidation
  task (shared coercion primitives parameterised on an error factory, plus a
  shared `scan_pattern`) would remove the duplication once, before any third
  pack family under §6/§7 adds a third copy, while keeping each package's typed
  error channel and messages unchanged.
- **Make the documentation commit gate green on `main` and keep it green.**
  `make markdownlint` has failed on the integration branch across two
  consecutive post-merge audits (7.1.1 Finding 7, 7.1.2 Finding 4) on the same
  recurring MD012 defect. A small task to fix the current breakage and to ensure
  the markdownlint gate runs against the full document on the implementing
  branch would stop the red baseline propagating.
