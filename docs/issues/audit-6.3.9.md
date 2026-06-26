# Post-merge audit — roadmap task 6.3.9

Audit of the codebase after roadmap task 6.3.9 ("Pin the developers'-guide
contract restatement against the code with a drift-guard arm") merged to `main`
at commit `1648249`. The task closes the *last* unguarded copy of the shared
interface contract: it adds
[`tests/test_developers_guide_contract_drift_guard.py`](../../tests/test_developers_guide_contract_drift_guard.py),
a docs-level drift-guard that pins the developers'-guide exit-code table and the
six-field JSON envelope brace-list to the live `ExitCode` enum, the `Envelope`
dataclass field order, and `ENVELOPE_SCHEMA_VERSION`. It extends the shared pure
scanner
[`tests/_skill_contract_scanner.py`](../../tests/_skill_contract_scanner.py)
with one helper, `extract_brace_field_list`, the fence-free counterpart of the
existing `extract_fenced_json`, because the guide names the envelope field set
inline as a `{...}` brace-list rather than in a `json` fence. No production
source under `novel_ralph_skill/` changed and no developers'-guide content
changed.

The merged change is high quality. The guard derives the field order and the
exit-code set from the *code* (`dataclasses.fields(Envelope)` and the `ExitCode`
enum), the two structural divergences from the 6.3.7 SKILL guard (a two-column
exit-code table; a fence-free inline brace-list) are documented with evidence
and exercised by planted-fixture unit tests, and a dedicated
`TestDevelopersGuideContractGuardNonVacuous` class proves the sliced regions are
non-empty so no guard passes vacuously. The new `extract_brace_field_list`
landed in the shared scanner sibling rather than in the guard module, keeping
both files under the 400-line cap. The three heading anchors the guard slices
between all resolve in order (`docs/developers-guide.md` lines 546, 596, 638).

Trail followed: `docs/novel-ralph-harness-design.md` §3.1/§3.2 (the envelope and
exit-code contract), `docs/adr-003-shared-interface-contract.md` (Table 2/Table
3), `docs/developers-guide.md` ("The shared JSON envelope" / "Disambiguated exit
codes" / the exit-3 formatter prose), `docs/scripting-standards.md` (actionable
prose), `AGENTS.md` (the 400-line cap, CQS, en-GB Oxford spelling), the
`python-router` skill (routing to `python-testing`), and `leta`/`sem` for
navigation and history. Files inspected:
`tests/test_developers_guide_contract_drift_guard.py`,
`tests/test_skill_contract_drift_guard.py`, `tests/_skill_contract_scanner.py`,
`tests/conftest.py`, `novel_ralph_skill/contract/envelope.py`,
`novel_ralph_skill/contract/exit_codes.py`,
`novel_ralph_skill/commands/_state_load.py`, `docs/developers-guide.md`, and
`docs/roadmap.md`.

The findings below are at the duplication, test-coverage, and documentation
layer; none is a correctness defect, and `make all` was green at merge. None is
applied here — this is a read-only audit step. Findings 1 to 3 are about the
two drift-guard modules now carrying byte-identical contract helpers; Finding 4
is a branch in the new scanner helper that no test exercises; Finding 5 records
that 6.3.9 pinned the guide's contract *vocabulary* but left a stale,
code-derived prose claim one section away unpinned and still wrong.

## Finding 1 — `_CODE_KEYWORDS` is duplicated byte-for-byte across the two contract guards

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`tests/test_developers_guide_contract_drift_guard.py`](../../tests/test_developers_guide_contract_drift_guard.py)
  lines 92-98 versus
  [`tests/test_skill_contract_drift_guard.py`](../../tests/test_skill_contract_drift_guard.py)
  lines 86-92.

Both contract guards carry an identical `_CODE_KEYWORDS: dict[ExitCode,
tuple[str, ...]]` mapping each `ExitCode` member to the keyword its Meaning cell
must contain (`SUCCESS: ("success",)`, `BENIGN_NEGATIVE: ("benign",)`,
`USAGE_ERROR: ("usage",)`, `STATE_ERROR: ("state",)`, `ACTIONABLE_FINDING:
("actionable", "finding")`). A `diff` of the two literals is empty. This table
is the load-bearing coupling each guard advertises in its docstring — "an enum
rename forces a keyword update here, which then re-pins the guide table" — yet
the table itself now lives in two places, so an `ExitCode` rename or a new
member must be reflected in two keyword tables, and the two can drift (one
updated, one not), which is exactly the single-source failure mode the §6.3
"documented once without drift" hypothesis exists to remove. The 6.3.9 module
docstring records the choice deliberately — "A small local copy is kept (rather
than importing the 6.3.7 guard's table) to avoid coupling two test modules
(ExecPlan WI2 Decision Log)" — but the rationale only argues against
test-module-to-test-module coupling; it does not argue against hosting the
table in the pure sibling
[`tests/_skill_contract_scanner.py`](../../tests/_skill_contract_scanner.py),
which both guards already import.

- **Proposed fix:** Promote `_CODE_KEYWORDS` (and its companion helper, Finding
  2) into the shared scanner module `tests/_skill_contract_scanner.py` — for
  example `code_meaning_keywords() -> dict[ExitCode, tuple[str, ...]]` or a
  module-level constant — keyed off the imported `ExitCode` enum, and have both
  guards import it. This keeps the single-source intent without introducing a
  guard-to-guard import: the dependency is each guard onto the pure helper
  module, the same edge both already have. A change to the keyword vocabulary
  then happens once. Keep the per-guard docstring note that the table is enum-
  derived, pointing at the shared definition. Proposed as a roadmap item below;
  not applied here.

## Finding 2 — `_meaning_has_keyword` is a second byte-identical helper across the two guards

- **Category:** similarity / duplication
- **Severity:** low
- **Location:**
  [`tests/test_developers_guide_contract_drift_guard.py`](../../tests/test_developers_guide_contract_drift_guard.py)
  lines 133-136 versus
  [`tests/test_skill_contract_drift_guard.py`](../../tests/test_skill_contract_drift_guard.py)
  lines 203-206.

The four-line `_meaning_has_keyword(meaning, keywords)` predicate — lowercase
the Meaning cell, return `any(keyword in lowered ...)` — is identical in both
guard modules (verified by `diff`). It is the matcher that consumes
`_CODE_KEYWORDS` (Finding 1), so the two travel together: the keyword table and
the function that interprets it are both copied. This is the same
extract-once-when-the-count-reaches-two threshold the 6.3.7 audit applied to the
fence regex and the document slicer.

- **Proposed fix:** Move `_meaning_has_keyword` into
  `tests/_skill_contract_scanner.py` alongside the keyword table from Finding 1
  (a single change discharges both) and have both guards import it. The helper
  is already pure over its two string arguments, so it fits the scanner module's
  "pure over document text" remit without modification. Proposed together with
  Finding 1 as one roadmap item below; not applied here.

## Finding 3 — `_envelope_field_order` is a third byte-identical helper across the two guards

- **Category:** similarity / duplication
- **Severity:** low
- **Location:**
  [`tests/test_developers_guide_contract_drift_guard.py`](../../tests/test_developers_guide_contract_drift_guard.py)
  lines 139-141 versus
  [`tests/test_skill_contract_drift_guard.py`](../../tests/test_skill_contract_drift_guard.py)
  lines 209-211.

Both guards define an identical `_envelope_field_order() -> list[str]` returning
`[field.name for field in dataclasses.fields(Envelope)]`. This is the canonical
field-order derivation the 6.3.7 audit (Finding 1) named as the right anchor —
the dataclass as single source — but 6.3.9 re-spells the derivation rather than
sharing it, so the count of hand-written copies of "derive the envelope field
order from the dataclass" in `tests/` has gone from one to two. Note this sits
adjacent to the still-open roadmap task 7.1.5, which already plans to promote a
shared `ENVELOPE_FIELD_ORDER` constant beside the `Envelope` definition in
`novel_ralph_skill/contract/envelope.py`; if that constant lands, both guards
should consume it and this duplication disappears.

- **Proposed fix:** Either (preferred) defer to roadmap task 7.1.5 and have both
  guards import the planned `ENVELOPE_FIELD_ORDER` constant from
  `novel_ralph_skill/contract/envelope.py` once it exists, deleting both local
  `_envelope_field_order` helpers; or, if 7.1.5 is not yet scheduled, host the
  single derivation in `tests/_skill_contract_scanner.py` as an interim shared
  helper. Avoid promoting a second standalone test-side copy. Folded into the
  Finding 1/2 roadmap item below as a coordination note with 7.1.5; not applied
  here.

## Finding 4 — the trailing-comma / empty-fragment branch of `extract_brace_field_list` is untested

- **Category:** test-gap
- **Severity:** low
- **Location:**
  [`tests/_skill_contract_scanner.py`](../../tests/_skill_contract_scanner.py)
  lines 266-269 (the `if field:` guard in `extract_brace_field_list`); the
  scanner's unit tests are
  [`tests/test_developers_guide_contract_drift_guard.py`](../../tests/test_developers_guide_contract_drift_guard.py)
  lines 257-275.

`extract_brace_field_list` documents that "Empty comma-split fragments (e.g. a
trailing comma) are discarded, so a cosmetic trailing comma does not introduce a
spurious blank field" and implements it with `if field:` before appending. The
five `TestDevelopersGuideContractScanner` cases cover ordered fields,
backtick-stripping, first-list selection, and the loud raise on a missing
brace-list, but none plants an input with a trailing comma (`{a, b,}`) or an
empty interior fragment (`{a,,b}`). The discard branch is therefore never
exercised: a regression that dropped the `if field:` guard (yielding a blank
field) would still pass every current test, and a mutation that removed it would
survive. The live developers'-guide brace-list carries no trailing comma, so the
guard does not currently rely on this branch — hence low severity — but the
branch is new code with documented behaviour and no test.

- **Proposed fix:** Add one unit case to `TestDevelopersGuideContractScanner`
  asserting `extract_brace_field_list("{a, b,}", source="planted") == ["a",
  "b"]` (and optionally `{a,,b}` for the interior-empty case), pinning the
  discard behaviour the docstring promises. A one-line test closes the gap.
  Proposed as a roadmap addendum below; not applied here.

## Finding 5 — 6.3.9 pinned the guide's contract vocabulary but left an adjacent, code-derived prose claim stale and unguarded

- **Category:** docs-gap
- **Severity:** medium
- **Location:** [`docs/developers-guide.md`](../../docs/developers-guide.md)
  line 619 ("Two sibling formatters …"); the 6.3.9 guard's exit-code region
  runs from line 596 to 638
  ([`tests/test_developers_guide_contract_drift_guard.py`](../../tests/test_developers_guide_contract_drift_guard.py)
  lines 81-82), spanning this prose but parsing only the markdown *table* within
  it.

The exit-3 paragraph at `docs/developers-guide.md:619` still reads "**Two**
sibling formatters in the dependency-free leaf module `_state_load` own the
prose." After roadmap task 6.3.8 there are **five** formatters in that module —
`_state_input_error`, `_draft_read_error`, `_compile_write_error`,
`_rule_pack_read_error`, and `_device_ledger_read_error` (verified at
`novel_ralph_skill/commands/_state_load.py` lines 94, 140, 189, 230, 271). This
is the same stale claim the audit-6.3.8 Finding 5 already raised and which the
roadmap already carries as the open addendum task 6.3.8.2
(`docs/roadmap.md:2388`); it is re-recorded here because 6.3.9 is the task that
*pinned this very guide section* yet the guard it added does not — and
structurally cannot — catch this drift. The guard slices the exit-code region
(lines 596-638) but `parse_markdown_table` reads only pipe-bearing rows, so the
prose sentence stating a verifiable code fact (the count of `_state_load`
formatters) is excluded. The §6.3 hypothesis the ExecPlan claims to fully
discharge — "the contract is documented once without per-command drift" — is
discharged for the exit-code *table* and the envelope *field set*, but a
code-derived count one paragraph below the table is wrong and unguarded. The
guide is a stated source of truth, hence the medium severity.

- **Proposed fix:** Two parts. (1) Complete the existing roadmap addendum 6.3.8.2
  to correct the prose to "Five sibling formatters" and name the three 6.3.8
  additions with their remedies — this is already scheduled and needs no new
  roadmap item. (2) Consider whether the 6.3.9 drift-guard should be widened, or
  a sibling arm added, to pin the formatter *count* (and ideally the formatter
  *names*) the guide states against the live set of `_state_input_error`-style
  symbols in `novel_ralph_skill/commands/_state_load.py`, so a future formatter
  added or removed without updating the guide fails a test — closing the gap
  that left the "Two/Five" claim drifting undetected through three tasks
  (6.3.7, 6.3.8, 6.3.9). Part (2) is proposed as a roadmap item below; part (1)
  defers to the open 6.3.8.2.

## Proposed roadmap items (for the root agent only)

- **Single-source the contract-guard helpers shared by the two prose guards**
  (severity: medium). Promote `_CODE_KEYWORDS` and `_meaning_has_keyword`
  (Findings 1-2) into the pure shared module
  [`tests/_skill_contract_scanner.py`](../../tests/_skill_contract_scanner.py)
  so the SKILL guard (6.3.7) and the developers'-guide guard (6.3.9) import one
  enum-keyed keyword table and one matcher rather than each carrying a byte-
  identical copy; coordinate with roadmap task 7.1.5 so the third duplicated
  helper, `_envelope_field_order` (Finding 3), consumes the planned shared
  `ENVELOPE_FIELD_ORDER` constant rather than a fourth test-side copy. Rationale:
  6.3.9 reproduces three byte-identical contract helpers from the 6.3.7 guard,
  re-creating the "documented once without drift" failure mode at the test layer
  the §6.3 hypothesis set out to remove, even though both guards already import
  the shared scanner module that could host them.

- **Guard the developers'-guide formatter-count prose against the `_state_load`
  formatter set** (severity: low). Add a drift-guard arm (or widen the 6.3.9
  guard) asserting the guide's exit-3 formatter prose names the count and set of
  `_state_load` exit-3 formatters that actually exist in
  `novel_ralph_skill/commands/_state_load.py`, so a formatter added or removed
  without updating the guide fails a test. Rationale: 6.3.9 pinned the guide's
  exit-code table and envelope field set but the adjacent "Two sibling
  formatters" prose — a code-derived count — has been stale since 6.3.8 and no
  guard catches it; pinning the count closes the last code-derived prose claim
  in the guide section the contract guards otherwise own. Coordinate with the
  open addendum 6.3.8.2, which corrects the prose itself.

- **Cover the trailing-comma branch of `extract_brace_field_list`** (severity:
  low). Add a unit case pinning that a trailing or interior empty comma fragment
  is discarded (Finding 4), exercising the `if field:` guard the docstring
  promises but no test reaches. Rationale: the discard branch is new 6.3.9 code
  with documented behaviour and zero coverage, so a regression removing it would
  pass every current test. A lightweight addendum, not a standalone step.
