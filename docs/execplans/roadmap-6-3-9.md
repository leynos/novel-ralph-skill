# Pin the developers'-guide contract restatement to the code with a drift-guard arm

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: COMPLETE

## Purpose / big picture

Roadmap task 6.3.9 closes the *last* unguarded copy of the shared interface
contract. The contract — the disambiguated exit-code vocabulary (design §3.2,
ADR-003 Table 2) and the six-field JSON envelope field set
(`{command, schema_version, ok, working_dir, result, messages}`, design §3.1) —
is restated in four reader-facing places:

1. `docs/adr-003-shared-interface-contract.md` (Table 2; the canonical decision
   record).
2. `docs/novel-ralph-harness-design.md` (§3.1 envelope skeleton; §3.2 exit-code
   table).
3. `docs/developers-guide.md` ("### The shared JSON envelope" and "###
   Disambiguated exit codes").
4. `skill/novel-ralph/SKILL.md` ("## Command contract").

Roadmap task 6.3.7 pinned copy 4 (`SKILL.md`) against the `ExitCode` enum, the
`Envelope` field set, `ENVELOPE_SCHEMA_VERSION`, and the canonical ADR-003 /
design copies, leaving a guarded trail through copies 1, 2, and 4. But copy 3 —
the developers' guide, which `SKILL.md` and the design doc point at as the
developer-facing canonical restatement — is itself pinned by **no** test. A
change to `novel_ralph_skill/contract/exit_codes.py`,
`novel_ralph_skill/contract/envelope.py`, or the guide's two contract sections
that is not kept in lockstep would silently stale the developer-facing copy: the
exact per-command drift roadmap step §6.3 exists to close.

After this change, a developer who edits the `ExitCode` enum, the envelope field
set, `ENVELOPE_SCHEMA_VERSION`, or the developers'-guide exit-code table /
envelope field-list without keeping them in lockstep gets a failing test naming
the divergence, rather than discovering the staleness later. Success is
observable by running the new test before the change (it fails on a planted
divergence) and after (it passes against the live `docs/developers-guide.md`),
and by running `make all`, `make markdownlint`, and `make nixie` green. With
this guard in place, every one of the four contract restatement copies is pinned
by a test, and the §6.3 "documented once without per-command drift" hypothesis
is fully discharged.

The mechanism is a docs-level *drift-guard*, following the repository's
established in-process *prose-guard* pattern (the shared `read_repo_text`
fixture, no subprocess, no `novel_ralph_skill` runtime behaviour). It reads
`docs/developers-guide.md`, extracts the exit-code-table rows and the inline
envelope field list, and asserts each tracks the live `ExitCode` enum, the live
`Envelope` field set and order, and `ENVELOPE_SCHEMA_VERSION`. The guard reuses
the pure parsing helpers already built for the 6.3.7 `SKILL.md` guard
(`tests/_skill_contract_scanner.py`) so it adds the smallest possible new
surface. The guard is mechanical, so it does not rely on reviewer diligence.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Work exclusively inside the git-donkey worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-9`. Never
  read-modify-write any file in the root/control worktree.
- This is a test-and-docs task. Do **not** modify production source under
  `novel_ralph_skill/` (in particular `contract/exit_codes.py`,
  `contract/envelope.py`, `commands/names.py`). The guard reads them; it must
  not change them. The roadmap success criterion is a guard, not a contract
  change.
- Do not change the *content* of the developers'-guide exit-code table, the
  envelope field-list, or the surrounding contract prose, nor of ADR-003 Table 2
  or design §3.1/§3.2. The guard pins the existing restatement; it is not a
  licence to re-edit the contract. The only permitted `docs/developers-guide.md`
  edit, if the guard's anchors demand it, is a whitespace-neutral clarification
  that does not change a documented value, recorded in the Decision Log with its
  justification.
- The new test must keep the repository's prose-guard discipline: it reads
  `docs/developers-guide.md` in process through the shared `read_repo_text`
  fixture (`tests/conftest.py`), does **not** shell out, and does **not** import
  `novel_ralph_skill` for its *runtime* side effects. It may import the contract
  *constants and enum* (`ExitCode`, the `Envelope` dataclass fields,
  `ENVELOPE_SCHEMA_VERSION`) — these are pure data, and importing them is what
  ties the guard to the code source the roadmap names. This mirrors
  `tests/test_skill_contract_drift_guard.py` (6.3.7) and
  `tests/test_contract_envelope_snapshots.py`, which already import the contract
  module directly.
- Keep the new test module under the 400-line cap the repository applies to test
  modules (AGENTS.md lines 24-27; see `tests/test_skill_contract_drift_guard.py`
  and `tests/test_state_layout_reference.py`, which extracted helpers to stay
  under it). Reuse the existing pure parser `tests/_skill_contract_scanner.py`;
  add a new pure helper to it only if a developers'-guide-specific parse (the
  inline field list) cannot be expressed with the existing functions.
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments,
  docstrings, and the commit message. 100% docstring coverage is enforced by
  `make lint`; every new module, class, function, and fixture needs a docstring.
- The integration branch is `main`; treat `origin/main` as canonical. Each work
  item is independently committable and must pass the full gate before commit.

## Tolerances (exception triggers)

- Scope: if implementation requires net changes to more than 3 files or more
  than 300 lines of code, stop and escalate. (Expected surface: one new test
  module, an optional 1-2-function addition to the existing
  `tests/_skill_contract_scanner.py`, and this execplan.)
- Interface: if pinning the contract requires changing any public API signature
  in `novel_ralph_skill/contract/`, stop and escalate — that would mean the
  guard cannot read the contract as data, which contradicts the task framing.
- Source divergence: if the guard reveals that `docs/developers-guide.md`
  already diverges from the live contract (a real, pre-existing drift rather
  than a planted one), stop and escalate. Fixing a live drift is a contract edit
  outside this task's scope; record it in the Decision Log and surface it.
- Dependencies: if a new external dependency is required, stop and escalate. No
  new dependency is expected; `pytest` and the existing scanner are already in
  the test toolchain.
- Iterations: if the new test still fails against the live, unplanted
  `docs/developers-guide.md` after 3 attempts to correct the *guard* (not the
  contract or the guide), stop and escalate.
- Ambiguity: if a load-bearing behavioural claim cannot be verified against the
  code or a cited document, stop and present options rather than guessing.

## Risks

    - Risk: Brittleness — a guard that pins whole sentences or exact table
      whitespace churns on every benign re-wording of the developers' guide.
      Severity: medium
      Likelihood: medium
      Mitigation: Pin semantic cells, not prose. Reuse
      `extract_exit_code_meanings` (column 0 → column 1 only) and compare the
      *set of codes* {0,1,2,3,4} exactly plus a small stable per-code *keyword*
      (success/benign/usage/state/actionable|finding) case-insensitively against
      the Meaning cell, exactly as the 6.3.7 SKILL guard does. For the envelope,
      pin the *field set and order* of the inline brace-list, not the
      surrounding prose.

    - Risk: (Structural divergence from the SKILL guard) The developers'-guide
      exit-code table has only TWO columns (Code, Meaning), whereas SKILL = 3,
      ADR-003 = 3, design §3.2 = 4. A guard copied verbatim from 6.3.7 that
      assumed a third "response" column would mis-read the guide.
      Severity: high
      Likelihood: high (if unaddressed)
      Mitigation: `extract_exit_code_meanings` is already column-count tolerant
      by design (it reads columns 0 and 1 and discards the rest; verified in
      `tests/_skill_contract_scanner.py` docstring lines 137-168). A two-column
      table is handled with no change. Add a planted-fixture unit assertion that
      a two-column table parses correctly, so the tolerance is pinned for the
      guide's shape specifically.

    - Risk: (Structural divergence from the SKILL guard — the envelope) The
      developers'-guide envelope section has NO fenced ```json skeleton. It
      states the field set inline as a single brace-list:
      `{command, schema_version, ok, working_dir, result, messages}` (line 549).
      `extract_fenced_json` would raise (no fence), so the SKILL guard's
      envelope half cannot be reused as-is.
      Severity: high
      Likelihood: high (if unaddressed)
      Mitigation: Verified: `sed -n '546,640p' docs/developers-guide.md | grep -c
      '```'` returns 0 — the section carries no fence. Add a small new pure
      helper `extract_brace_field_list(region, *, source)` to
      `tests/_skill_contract_scanner.py` that finds the first `{...}` brace-list
      in the region and returns its comma-split, stripped, backtick-stripped
      field names in order. Pin the returned list against
      `[f.name for f in dataclasses.fields(Envelope)]`. This is the documented,
      scoped alternative to `extract_fenced_json` for the guide's prose form; it
      does NOT replace the SKILL fence path, which stays.

    - Risk: schema_version is not a *value* in the guide's envelope field-list.
      Unlike the SKILL/design fenced skeletons (which carry `"schema_version":
      1`), the guide names `schema_version` only as a field name in the
      brace-list; its *value* (1) is documented in prose elsewhere
      (`ENVELOPE_SCHEMA_VERSION`'s relationship to the state.toml and rule-pack
      versions, lines 549-561 and ADR-003 lines 60-61), not as a literal `1` in
      this section. A naive "assert the parsed schema_version equals
      ENVELOPE_SCHEMA_VERSION" copied from the SKILL guard would have nothing to
      parse and would false-fail or vacuously pass.
      Severity: medium
      Likelihood: high (if unaddressed)
      Mitigation: For the guide, pin `schema_version` as a *field name present in
      the brace-list and in field order* (the `Envelope` field set/order check
      already covers this), NOT as a literal value in this section. Importing
      `ENVELOPE_SCHEMA_VERSION` still ties the guard to the constant via the
      field-set coupling; do not invent a value assertion the source text does
      not carry. Record this carve-out in the Decision Log and the test
      docstring so a future reader does not "tighten" it into a false failure.

    - Risk: The guard imports the contract module, coupling a docs test to
      production code import-time behaviour.
      Severity: low
      Likelihood: low
      Mitigation: The contract modules (`envelope.py`, `exit_codes.py`) are pure
      data and side-effect-free at import — verified: `envelope.py` has no
      top-level I/O (only docstring, `TYPE_CHECKING` imports, the
      `ENVELOPE_SCHEMA_VERSION` constant, and the frozen dataclass);
      `exit_codes.py` is an `IntEnum` plus `is_ok`. `tests/test_skill_contract_
      drift_guard.py` (6.3.7) and `tests/test_contract_envelope_snapshots.py`
      already import them. Importing `ExitCode`, the `Envelope` dataclass fields,
      and `ENVELOPE_SCHEMA_VERSION` is the *point* — it ties the guide's
      restatement to the code source the roadmap names.

    - Risk: The drift-guard could pass vacuously if a heading anchor is renamed
      and the region comes back empty.
      Severity: medium
      Likelihood: low
      Mitigation: Reuse `slice_doc_region(text, start, end, *, source)`
      (`tests/_skill_contract_scanner.py` lines 53-96), which fails loudly when
      either anchor is missing. Add an explicit `test_regions_are_non_empty`
      asserting the guide's exit-table region contains its `| 0 |` code row and
      the envelope region contains `schema_version`, so a renamed "###
      Disambiguated exit codes" / "### The shared JSON envelope" heading fails
      rather than silently passing. The new `extract_brace_field_list` raises on
      a missing brace-list, same vacuous-pass discipline as `extract_fenced_json`.

    - Risk: Two `{...}` brace-lists could appear in the envelope region (e.g.
      the field-list plus an inline example), so "the first brace-list" could
      pull the wrong one.
      Severity: low
      Likelihood: low
      Mitigation: Verified the §3 "### The shared JSON envelope" region of
      `docs/developers-guide.md` (lines 546-595): the only `{...}` brace-list in
      it is the field-list at line 549. The `extract_brace_field_list` helper
      takes the first brace-list in the region it is given; the caller narrows to
      the envelope section first via `slice_doc_region`. Add a non-vacuous
      assertion that the extracted list contains `working_dir` and exactly the
      six fields, so a future reshuffle that introduces a second, shorter
      brace-list fails loudly rather than silently picking it.

## Progress

    - [x] Work item 1: Add a failing drift-guard skeleton (folded into Work item
      2's commit to keep every commit gate-green). Done: the guard module and the
      `extract_brace_field_list` helper landed as one atomic commit; no broken
      commit was created.
    - [x] Work item 2: Exit-code-table drift guard against `ExitCode` (code set
      exact; per-code Meaning keyword; column-count tolerant for the guide's
      two-column table). Done: `TestDevelopersGuideExitCodeTableDriftGuard` plus
      the two-column scanner unit tests.
    - [x] Work item 3: Envelope field-list drift guard against the `Envelope`
      field set/order (inline brace-list, no fence), with the
      `schema_version`-as-field-name carve-out documented. Done: new
      `extract_brace_field_list` helper and
      `TestDevelopersGuideEnvelopeFieldListDriftGuard`.
    - [x] Work item 4: Vacuous-pass hardening and planted-divergence red/green
      proof; final docs gates. Done: `test_regions_are_non_empty`; both red
      proofs captured (Artefacts); no collection-count tripwire found; `make
      all`, `make markdownlint`, and `make nixie` green.

## Surprises & discoveries

    - The four work items form one coherent, indivisible new test module plus one
      pure helper. Per the plan's own "fold WI1 into WI2 to keep every commit
      gate-green" guidance, and because splitting the module across commits would
      either land a broken commit (the helper before its caller, or the caller
      before its helper) or churn the same file repeatedly, the whole guard was
      shipped as a single atomic, gate-green commit. The Progress section still
      ticks each work item's deliverable; they all land together.
    - `coderabbit review --agent` returned 0 findings on the change, so no review
      remediation was required.

## Decision log

    - Decision: cuprum and the other locked external libraries (Cyclopts,
      pytest-timeout, uv) are NOT load-bearing for this task; the plan uses none
      of them.
      Rationale: The roadmap success criterion is a docs-level drift-guard that
      reads `docs/developers-guide.md` text in process and compares it against
      the in-repo `ExitCode` / `Envelope` / `ENVELOPE_SCHEMA_VERSION` constants.
      It runs no subprocess, builds no command catalogue, and executes no
      installed binary. This mirrors the sibling 6.3.7 guard
      (`tests/test_skill_contract_drift_guard.py`) and the prose-guards it copies
      (`tests/test_skill_deflation_guard.py`,
      `tests/test_state_layout_reference.py`), which read files through
      `read_repo_text` with no cuprum, no Cyclopts, and no uv. The
      contract-source coupling is a plain Python import of pure data (verified:
      `envelope.py` and `exit_codes.py` do no I/O at import), exactly as
      `tests/test_contract_envelope_snapshots.py` already does. Pinning a cuprum
      API here would justify a mechanism the task does not use; it is therefore
      scoped out explicitly rather than hedged. (Confirmed against the LOCKED
      cuprum source at `/data/leynos/Projects/cuprum`: catalogue/program/sh
      construction is irrelevant to an in-process text guard.)
      Date/Author: 2026-06-26, planner

    - Decision: Reuse the existing `tests/_skill_contract_scanner.py` parser
      rather than create a second scanner module.
      Rationale: That module's `slice_doc_region`, `parse_markdown_table`, and
      `extract_exit_code_meanings` are pure functions over document text that
      already handle a variable-column exit-code table (column-count tolerant).
      The guide's two-column table needs no new exit-code parser. Only the inline
      brace-list envelope form is new, so a single small helper
      (`extract_brace_field_list`) is added to that module. Reusing the module
      keeps the new test surface minimal and the parser independently unit-tested
      in one place. The module is correctly named for "skill contract" but its
      functions are document-generic; if the name becomes misleading, a rename is
      a separate refactor (Tolerances: scope) — not folded in here.
      Date/Author: 2026-06-26, planner

    - Decision: For the developers' guide, pin `schema_version` as a *field name*
      in the brace-list and in `Envelope` field order, NOT as a literal value.
      Rationale: Verified — the guide's envelope section
      (`docs/developers-guide.md` lines 546-595) names the field set inline as
      `{command, schema_version, ok, working_dir, result, messages}` (line 549)
      and carries NO fenced JSON skeleton and NO literal `schema_version: 1` in
      this section (`grep -c '```'` over lines 546-640 returns 0). The
      SKILL/design fenced skeletons carry the literal `1`; the guide does not.
      Pinning a non-existent value would be a false-fail or a vacuous pass. The
      field-set/order coupling to `Envelope` (which includes `schema_version`)
      plus the import of `ENVELOPE_SCHEMA_VERSION` is the load-bearing tie; the
      literal-value assertion belongs to the SKILL/design guards, not this one.
      Date/Author: 2026-06-26, planner

    - Decision: The exit-code Meaning column is compared by per-code *keyword*,
      not exact string, and the guide table is read column-count-tolerantly.
      Rationale: Verified the guide's Meaning wording differs from the other
      copies (guide "State or input error; recover state before retrying" vs
      ADR-003 "State or input error"; guide "Actionable finding a deterministic
      detector has surfaced" vs ADR-003 "Actionable findings requiring agent
      intervention"). Exact-string equality would false-fail. `extract_exit_code_
      meanings` already keys column 0 → column 1 and ignores later columns, so
      the guide's two-column table is read with no special case. The per-code
      keyword set is derived from the `ExitCode` enum members, not copied from
      the guide, which is the load-bearing coupling.
      Date/Author: 2026-06-26, planner

## Outcomes & retrospective

    - Outcome: roadmap task 6.3.9 is complete. The developers'-guide command-
      contract restatement (the "### Disambiguated exit codes" two-column table
      and the "### The shared JSON envelope" inline brace-list) is now pinned by
      `tests/test_developers_guide_contract_drift_guard.py` against the live
      `ExitCode` enum, the `Envelope` field set/order, and
      `ENVELOPE_SCHEMA_VERSION`. With this guard in place all four restatement
      copies (ADR-003 Table 2, design §3.1/§3.2, the developers' guide, and
      `SKILL.md`) are pinned by a test, discharging the §6.3 "documented once
      without per-command drift" hypothesis.
    - Retrospective: the plan's two structural-divergence predictions held
      exactly. The existing `extract_exit_code_meanings` read the guide's
      two-column table with no change, and the new `extract_brace_field_list`
      handled the fence-free inline field-list. No live drift was found (no
      Tolerance breach), no production source changed, and the change stayed well
      within the 3-file / 300-line scope tolerance. `coderabbit review --agent`
      returned 0 findings.

## Context and orientation

This repository is a Python skill (`skill/novel-ralph/`) plus its supporting
package (`novel_ralph_skill/`) and a `tests/` tree. The shared interface
contract — how every `novel` command reports to the harness — is defined once in
code and restated in several reader-facing documents.

The canonical contract sources, by full path:

- `novel_ralph_skill/contract/exit_codes.py` defines
  `class ExitCode(enum.IntEnum)` with members `SUCCESS = 0`,
  `BENIGN_NEGATIVE = 1`, `USAGE_ERROR = 2`, `STATE_ERROR = 3`,
  `ACTIONABLE_FINDING = 4`, and `is_ok(code)` (the `ok` biconditional). This is
  the code source of the exit-code vocabulary. Verified side-effect-free at
  import.
- `novel_ralph_skill/contract/envelope.py` defines
  `ENVELOPE_SCHEMA_VERSION: int = 1` and the frozen `Envelope` dataclass whose
  fields, in order, are `command`, `schema_version`, `ok`, `working_dir`,
  `result`, `messages` (verified at lines 55-60). This is the code source of the
  envelope field set, order, and schema version. Verified side-effect-free at
  import (no top-level I/O).

The restatement site this task pins, by full path:

- `docs/developers-guide.md` — two sections:
  - "### The shared JSON envelope" (heading verified at line 546; next H3 "###
    Disambiguated exit codes" at line 596). Its first sentence names the field
    set inline as a brace-list:
    `{command, schema_version, ok, working_dir, result, messages}` (line 549).
    There is **no** fenced JSON skeleton in this section.
  - "### Disambiguated exit codes" (heading verified at line 596; next H3 "###
    State and on-disk layout" at line 638). Its markdown table (lines 601-607)
    has TWO columns (Code, Meaning) — narrower than the SKILL (3), ADR-003 (3),
    and design §3.2 (4) copies. **This is the one restatement copy no test
    pins.** All anchoring is by heading text, not line number; line numbers above
    are orientation only and may drift.

The other three restatement copies (`docs/adr-003-shared-interface-contract.md`
Table 2; `docs/novel-ralph-harness-design.md` §3.1/§3.2;
`skill/novel-ralph/SKILL.md`) are already pinned: ADR-003 and the design doc are
the canonical/source copies and are cross-checked by, and `SKILL.md` is pinned
by, the 6.3.7 guard `tests/test_skill_contract_drift_guard.py`.

The established prose-guard pattern this plan reuses:

- `tests/test_skill_contract_drift_guard.py` (roadmap 6.3.7) reads `SKILL.md`
  through the `read_repo_text` fixture, slices it by heading anchors, parses the
  exit-code table and envelope skeleton, and asserts each cell tracks the live
  `ExitCode`/`Envelope`/`ENVELOPE_SCHEMA_VERSION`. This task is its direct
  sibling for the developers' guide.
- `tests/_skill_contract_scanner.py` holds the pure parsing helpers:
  `slice_doc_region(text, start, end, *, source)` (loud-failure region slicer),
  `parse_markdown_table(region)` (column-count-tolerant table parser),
  `extract_exit_code_meanings(rows)` (code → Meaning, columns 0-1 only), and
  `extract_fenced_json(region, fence_lang)` (first fence, loud on absence). The
  first three are reused unchanged; this task adds `extract_brace_field_list`
  for the guide's fence-free inline field set.
- `tests/test_skill_deflation_guard.py` and
  `tests/test_state_layout_reference.py` show the helper-extraction discipline
  and the 400-line-cap convention.

The shared fixture: `tests/conftest.py` defines `read_repo_text` (an in-process
repo-relative UTF-8 reader, verified at lines 153-170) and the `RepoTextReader`
protocol; `project_root` gives the worktree root. These are the only scaffolding
the guard needs.

Term definitions:

- *Drift-guard*: a test that fails when two copies of the same fact (here, the
  developers'-guide restatement and the code source) diverge.
- *Prose-guard*: the repository's name for an in-process test that reads a
  documentation file as text and asserts mechanical properties of it without
  shelling out.
- *Field-list*: the inline `{command, schema_version, ...}` brace-list that
  names the envelope fields in contract order in the developers' guide (in place
  of a fenced JSON skeleton).

## Plan of work

The work proceeds red-first (a failing skeleton), then builds the two guard
halves (exit-code table, envelope field-list), then hardens against vacuous
passes and proves red/green on a planted divergence. Each work item is a single
commit that passes `make all`, `make markdownlint`, and `make nixie`.

Decision before writing code (resolved, no fork): the guard lives in a new
module `tests/test_developers_guide_contract_drift_guard.py`. The exit-code
parsing reuses `tests/_skill_contract_scanner.py` unchanged; the only new pure
helper is `extract_brace_field_list`, added to that same scanner module so the
parser stays in one independently-unit-tested place and the guard module stays
under the 400-line cap.

- Stage A (Work item 1): scaffolding and a red test.
- Stage B (Work items 2-3): the two guard halves.
- Stage C (Work item 4): vacuous-pass hardening, planted-divergence red/green
  proof, and final docs gates.

Each stage ends with `make all`. Do not proceed to the next stage on a red gate.

## Concrete steps

All commands run from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-9`.

### Work item 1 — Failing drift-guard skeleton (Stage A)

Implements: the roadmap 6.3.9 success criterion ("a drift-guard arm fails if the
developers'-guide exit-code table or envelope-field vocabulary diverges … the
guard reuses the repo's established prose-guard pattern"); AGENTS.md
"Establish a failing test suite prior to implementation (red, green,
refactor)" (lines 66-67).

Docs to read first: `docs/roadmap.md` task 6.3.9 (the "Pin the developers'-guide
contract restatement" block); the execplans skill (red-green-refactor, mandatory
living sections); AGENTS.md testing rules (lines 141-172). Read the sibling
`docs/execplans/roadmap-6-3-7.md` end to end — this task is its direct analogue.

Skills to load: `leta` first for navigation; `sem` for history;
`python-router` (it routes to `python-testing` for the pytest
fixture/parametrize idiom and to `python-types-and-apis` for the `RepoTextReader`
protocol import).

Create `tests/test_developers_guide_contract_drift_guard.py` with:

- A module docstring stating it pins the `docs/developers-guide.md`
  command-contract restatement (the "### Disambiguated exit codes" table and the
  "### The shared JSON envelope" field-list) to `ExitCode`, the `Envelope` field
  set, and `ENVELOPE_SCHEMA_VERSION`, following the prose-guard pattern of
  `tests/test_skill_contract_drift_guard.py`, and naming the
  schema_version-as-field-name carve-out (Decision Log).
- A `_GUIDE_PARTS = ("docs", "developers-guide.md")` constant and a `guide_text`
  fixture over `read_repo_text`, mirroring the 6.3.7 guard's `skill_text`
  fixture.
- One *placeholder* assertion that intentionally fails (e.g. asserting a sentinel
  the file does not contain), so the suite is red before the guard exists.

Run the new module and confirm it is collected and red:

    uv run pytest -q tests/test_developers_guide_contract_drift_guard.py

Expected: 1 failed (the placeholder), 0 errors (the module imports and the
fixture resolves). Then run the gate:

    make all

Expected: the only failure is the planted placeholder in the new module. Commit
is deferred until the placeholder is replaced; preferred path: fold Work item 1
into Work item 2's commit so no broken commit lands (Decision recorded below:
ship Work items 1+2 as one commit to keep every commit gate-green).

### Work item 2 — Exit-code-table drift guard (Stage B)

Implements: roadmap 6.3.9 ("fails if the developers'-guide exit-code table …
diverges from the `ExitCode` … source"); design §3.2
(`docs/novel-ralph-harness-design.md`); ADR-003 Table 2
(`docs/adr-003-shared-interface-contract.md`);
`novel_ralph_skill/contract/exit_codes.py`.

Docs to read first: the guide's "### Disambiguated exit codes" section
(`docs/developers-guide.md` heading line 596, two-column table lines 601-607);
`exit_codes.py` (the five enum members); the 6.3.7 guard's exit-code half
(`tests/test_skill_contract_drift_guard.py`,
`TestSkillExitCodeTableDriftGuard`). Skills: `python-router` →
`python-testing`.

No new scanner function is needed for the exit-code half: reuse
`slice_doc_region`, `parse_markdown_table`, and `extract_exit_code_meanings` from
`tests/_skill_contract_scanner.py` (the last is already column-count tolerant, so
the guide's two-column table parses unchanged).

In `tests/test_developers_guide_contract_drift_guard.py` add:

- An `_EXIT_HEADING = "### Disambiguated exit codes"` anchor and an
  `_EXIT_END = "### State and on-disk layout"` anchor; an `exit_table_region`
  fixture slicing the guide between them via
  `slice_doc_region(guide_text, _EXIT_HEADING, _EXIT_END, source="developers-guide.md")`.
- A `_CODE_KEYWORDS: dict[ExitCode, tuple[str, ...]]` derived from the enum:
  `SUCCESS → ("success",)`, `BENIGN_NEGATIVE → ("benign",)`,
  `USAGE_ERROR → ("usage",)`, `STATE_ERROR → ("state",)`,
  `ACTIONABLE_FINDING → ("actionable", "finding")`. Keying off the enum member,
  not a string copied from the guide, is the load-bearing coupling. (This may be
  imported from, or duplicated from, the 6.3.7 guard; prefer a small local copy
  to avoid coupling two test modules, and note the choice in the Decision Log.)
- `test_guide_exit_codes_cover_exactly_the_enum`: parse the guide's table with
  `parse_markdown_table` + `extract_exit_code_meanings`, assert the set of
  integer codes equals `{c.value for c in ExitCode}` (i.e. `{0,1,2,3,4}`).
  Adding or removing an enum member without updating the table fails here.
- `test_guide_exit_code_meanings_match_keywords`: for each `ExitCode`, assert at
  least one of its `_CODE_KEYWORDS` appears (case-insensitively) in the guide's
  Meaning cell for that code. Pin keywords, not whole sentences (Risks:
  brittleness; Decision Log: keyword-not-exact-string).

Tests to add/update (per AGENTS.md): the above are unit/prose-guard tests in
`tests/`. Add a small unit test class `TestDevelopersGuideContractScanner` (or
extend the scanner's existing unit tests in the 6.3.7 module) that drives
`parse_markdown_table` + `extract_exit_code_meanings` over a *planted*
two-column in-string table fixture (a multi-line literal, not a file) to prove
the column-count-tolerant path reads a two-column table correctly — the
guide-specific shape (Risks: structural divergence). No snapshot test is
warranted (AGENTS.md lines 148-158: avoid snapshot-only coverage for logic
assertable directly). No property test is warranted: the inputs are fixed in-repo
documents, not a generative surface (AGENTS.md lines 162-163).

Validation:

    uv run pytest -q tests/test_developers_guide_contract_drift_guard.py
    make all
    make markdownlint
    make nixie

Expected: all new tests pass; full suite green; markdown gates green (no markdown
changed in this item, but run them to confirm the gate). Commit this work item
(folding in Work item 1's scaffolding) with a message referencing roadmap 6.3.9.

### Work item 3 — Envelope field-list drift guard (Stage B)

Implements: roadmap 6.3.9 ("fails if the developers'-guide … envelope-field
vocabulary diverges from the … envelope-field, and schema_version source");
design §3.1 (`docs/novel-ralph-harness-design.md`);
`novel_ralph_skill/contract/envelope.py` (the `Envelope` dataclass fields and
`ENVELOPE_SCHEMA_VERSION`).

Docs to read first: the guide's "### The shared JSON envelope" section
(`docs/developers-guide.md` heading line 546, inline field-list line 549, next
H3 at line 596); `envelope.py` (the dataclass field order, lines 55-60, and
`ENVELOPE_SCHEMA_VERSION` at line 25); the 6.3.7 guard's envelope half. Skills:
`python-router` → `python-testing`, `python-data-shapes` (dataclass field
introspection via `dataclasses.fields`).

Add the new pure helper to `tests/_skill_contract_scanner.py`:

- `extract_brace_field_list(region: str, *, source: str) -> list[str]` — finds
  the FIRST `{...}` brace-list in the region, splits it on commas, strips
  surrounding whitespace and backticks from each field, and returns the field
  names in order. Raises `ValueError` (naming `source`) if the region holds no
  brace-list (vacuous-pass guard, mirroring `extract_fenced_json`). Its docstring
  states it is the fence-free counterpart used for the developers' guide, whose
  envelope section names the field set inline rather than in a ```json fence.
  Keep it pure (no filesystem, no `novel_ralph_skill` import) like its siblings.

Add to `tests/test_developers_guide_contract_drift_guard.py`:

- An `_ENVELOPE_HEADING = "### The shared JSON envelope"` anchor and an
  `_ENVELOPE_END = "### Disambiguated exit codes"` anchor; an `envelope_region`
  fixture: `slice_doc_region(guide_text, _ENVELOPE_HEADING, _ENVELOPE_END,
  source="developers-guide.md")`.
- A `guide_envelope_fields` fixture: `extract_brace_field_list(envelope_region,
  source="developers-guide.md")`.
- `test_guide_envelope_fields_match_dataclass`: assert `guide_envelope_fields`
  equals `[f.name for f in dataclasses.fields(Envelope)]` — i.e.
  `["command", "schema_version", "ok", "working_dir", "result", "messages"]`.
  This pins the field set **and order** to the code (the contract field order is
  load-bearing; `render_machine` asserts it too). A field renamed, reordered,
  added, or dropped in the guide's brace-list, or in the dataclass, fails here.
- `test_guide_envelope_names_schema_version_field`: assert `"schema_version"` is
  in `guide_envelope_fields`. Per the Decision Log carve-out, this pins
  schema_version as a *field name in contract position*, NOT as a literal value
  (the guide carries no `schema_version: 1` literal in this section). Document
  the carve-out in the test docstring so a future reader does not "tighten" it
  into a non-existent value assertion. The import of `ENVELOPE_SCHEMA_VERSION` at
  module top ties the guard to the constant; reference it in the docstring's
  rationale even though the section carries no literal to compare.

Tests to add (per AGENTS.md): unit/prose-guard tests as above. Extend the scanner
unit-test class with planted fixtures proving (a) `extract_brace_field_list`
returns the ordered field names from a planted `{a, b, c}` literal and strips
backticks, and (b) it raises `ValueError` on a region with no brace-list. No
snapshot/property test warranted (same reasoning as Work item 2).

Validation: the same command quartet as Work item 2; all green. Commit
referencing roadmap 6.3.9.

### Work item 4 — Vacuous-pass hardening and planted-divergence proof (Stage C)

Implements: roadmap 6.3.9 success criterion's "fails if … diverges" — proven by
demonstrating red on a planted divergence; AGENTS.md "a failing test before the
fix and a passing test that would have caught the regression" (lines 66-71) and
the snapshot/guard discipline that "a … guard failure identifies a real contract
change" (lines 156-158).

Docs to read first: the 6.3.7 guard's vacuous-pass class
(`tests/test_skill_contract_drift_guard.py`, the non-vacuous test) and the
scanner's loud-failure helpers. Skills: `python-router` → `python-testing`;
optionally `python-verification` to confirm no generative/property adversary is
warranted (it is not — fixed-document inputs).

Steps:

1. Audit every anchor lookup and region slice in the guard. Confirm each uses the
   loud-failure helpers (`slice_doc_region` with its `source` label,
   `extract_brace_field_list`'s missing-brace-list raise) so a renamed heading or
   removed field-list fails rather than yielding an empty region that passes
   vacuously. Add an explicit `test_regions_are_non_empty` asserting the guide's
   exit-table region contains `| 0 |` and the envelope region contains
   `schema_version` and exactly the six expected fields (so a future heading
   rename or a second stray brace-list cannot silently neuter the guard).
2. Prove the guard is genuinely red on divergence, *without committing a broken
   guide*. Do this with a transient local edit during development: temporarily
   delete the `| 4 | … |` exit-code row in `docs/developers-guide.md`, run
   `uv run pytest -q tests/test_developers_guide_contract_drift_guard.py`,
   observe `test_guide_exit_codes_cover_exactly_the_enum` fail, then revert.
   Likewise temporarily rename `working_dir` to `workdir` in the envelope
   brace-list and observe `test_guide_envelope_fields_match_dataclass` fail, then
   revert. Record both transcripts in `Artifacts and notes`. (These edits are
   never committed; they are the red-test evidence the execplans skill and
   AGENTS.md require. `git checkout -- docs/developers-guide.md` restores the
   file; confirm `git status` is clean of the guide before committing.)
3. Confirm no test-collection inventory tripwire. The 6.3.7 plan traced
   (`docs/execplans/roadmap-6-3-7.md`, B3 Decision-Log entry) that there is NO
   collected-test-module-count assertion, `tests/`-directory inventory frozenset,
   or `pytest_collect*` hook in the suite, so a new `tests/` module breaks no
   gate. Re-confirm with a quick search; if, contrary to that trace, a
   collection-count guard is encountered, that is a Tolerance breach — stop and
   escalate rather than editing it.
4. Final docs gate, since the guard is docs-adjacent: run the full quartet.

Validation:

    make all
    make markdownlint
    make nixie

Expected: all green; the new module's tests pass against the live, reverted
`docs/developers-guide.md`. Commit referencing roadmap 6.3.9, then update
`Progress`, `Outcomes & retrospective`, and the Status header to reflect
completion.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: the new `tests/test_developers_guide_contract_drift_guard.py` passes
  against the live `docs/developers-guide.md`; it fails (demonstrated
  transiently) when the guide's exit-code table loses/gains a code and when an
  envelope field in the brace-list is renamed, reordered, added, or dropped. The
  6.3.7 guard (`tests/test_skill_contract_drift_guard.py`) and the contract suite
  (`tests/test_contract_*`) stay green.
- Lint/typecheck: `make lint` passes (Ruff, 100% docstring coverage, pyright/ty
  as configured). `make all` is green end to end.
- Markdown: `make markdownlint` and `make nixie` pass (no Mermaid added; run to
  confirm the gate, per AGENTS.md lines 169-172).
- No production source under `novel_ralph_skill/` changed (verify with
  `git diff --name-only`; expected paths are only under `tests/` and this
  execplan, plus at most a whitespace-neutral `docs/developers-guide.md`
  clarification recorded in the Decision Log).

Quality method (how we check):

- Run `make all` before and after each work item; run the markdown quartet on
  the final item. Use `git diff --name-only` to confirm the change surface
  matches the Constraints.
- The acceptance behaviour a human can verify: "Run
  `uv run pytest -q tests/test_developers_guide_contract_drift_guard.py` and
  expect all tests passing; temporarily rename `working_dir` to `workdir` in the
  `### The shared JSON envelope` brace-list of `docs/developers-guide.md`,
  re-run, and expect `test_guide_envelope_fields_match_dataclass` to fail;
  revert."

## Idempotence and recovery

- All steps are re-runnable. The guard reads files; it writes only new test files
  (and one new helper appended to `tests/_skill_contract_scanner.py`). Re-running
  `make all` is safe.
- The Work item 4 red-test demonstration uses transient, never-committed edits to
  `docs/developers-guide.md`; if interrupted mid-edit,
  `git checkout -- docs/developers-guide.md` restores it. Confirm `git status` is
  clean of the guide before committing.
- If the guard reveals a *real* pre-existing drift between the guide and the live
  contract (a Tolerance breach), stop, do not "fix" it by editing the contract or
  the table, and escalate per the Tolerances section.

## Artefacts and notes

Captured during implementation (the `docs/developers-guide.md` edits are
transient and reverted; `git status` confirms the guide clean before each
commit):

- Red, deleted exit-code row (the `| 4 | … |` row removed transiently):
  `test_guide_exit_codes_cover_exactly_the_enum` FAILED with
  `Extra items in the right set: 4` (the parsed set `{0,1,2,3}` no longer equals
  `{0,1,2,3,4}`). Guide reverted; `git status` clean. CONFIRMED.
- Red, renamed envelope field (`working_dir` → `workdir` transiently):
  `test_guide_envelope_fields_match_dataclass` FAILED with
  `At index 3 diff: 'workdir' != 'working_dir'`. Guide reverted; `git status`
  clean. CONFIRMED.
- Green against the reverted, live guide: the guard module's 11 tests pass; full
  `make all` green (1370 passed, 1 skipped). CONFIRMED.
- No test-collection inventory tripwire: a search for `pytest_collect`,
  `frozenset.*test_`, `collected.*count`, and `len(.glob(...test...))` over
  `tests/` returned nothing, confirming the 6.3.7 trace; a new `tests/` module
  breaks no gate. CONFIRMED.
- Change surface: `tests/_skill_contract_scanner.py` (the new
  `extract_brace_field_list` helper and docstring note),
  `tests/test_developers_guide_contract_drift_guard.py` (new), and
  `docs/execplans/roadmap-6-3-9.md` (this plan) — plus the roadmap tick in
  `docs/roadmap.md`. No file under `novel_ralph_skill/` changed and no
  `docs/developers-guide.md` content changed. CONFIRMED.

## Interfaces and dependencies

Libraries/modules to use and why:

- `pytest` with the shared `read_repo_text` fixture (`tests/conftest.py`) — the
  sanctioned in-process repo-text reader; no subprocess, matching the prose-guard
  discipline.
- `novel_ralph_skill.contract.exit_codes.ExitCode` — imported as pure data to
  derive the expected code set and per-code keywords, tying the guide's table to
  the code source named by the roadmap.
- `novel_ralph_skill.contract.envelope.Envelope` (via `dataclasses.fields`) and
  `ENVELOPE_SCHEMA_VERSION` — imported to derive the expected field order and to
  tie the guard to the schema-version constant (as a field-name coupling; see the
  Decision Log carve-out).
- `dataclasses` (stdlib) for field introspection.
- The pure scanner `tests/_skill_contract_scanner.py` — reused for
  `slice_doc_region`, `parse_markdown_table`, `extract_exit_code_meanings`, and
  extended with the new `extract_brace_field_list`. No new external dependency.

Symbols that must exist at the end of the milestone:

    # tests/_skill_contract_scanner.py  (new pure function appended)
    def extract_brace_field_list(region: str, *, source: str) -> list[str]: ...
        # first {...} brace-list -> ordered, stripped, backtick-free field
        # names; raises ValueError naming `source` when absent (vacuous guard)

    # tests/test_developers_guide_contract_drift_guard.py
    class TestDevelopersGuideExitCodeTableDriftGuard: ...    # WI2
    class TestDevelopersGuideEnvelopeFieldListDriftGuard: ...  # WI3
    class TestDevelopersGuideContractScanner: ...           # parser unit tests
    class TestDevelopersGuideContractGuardNonVacuous: ...    # WI4

No new external dependency is introduced. No public API in `novel_ralph_skill/`
changes.

## Revision note

Initial draft (2026-06-26). Decomposes roadmap 6.3.9 into four ordered,
independently committable work items: red skeleton (folded into WI2 to keep every
commit gate-green), exit-code-table guard, envelope-field-list guard, and
vacuous-pass hardening with a planted-divergence red/green proof. The plan is the
direct sibling of `docs/execplans/roadmap-6-3-7.md` (the `SKILL.md` guard) and
reuses its pure scanner `tests/_skill_contract_scanner.py`. Two structural
divergences from the SKILL guard are pinned with verified evidence: the
developers'-guide exit-code table has only two columns (handled by the existing
column-count-tolerant `extract_exit_code_meanings`), and the envelope section
carries an inline `{...}` field-list rather than a fenced JSON skeleton (handled
by a new `extract_brace_field_list` helper). The `schema_version`-as-field-name
carve-out — the guide names the field but carries no literal `1` in this section
— is recorded so the guard pins the field, not a non-existent value. cuprum and
the other locked external libraries are scoped out explicitly with rationale
(Decision Log): the task is an in-process docs drift-guard that uses none of them.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
post-merge reviews and audits. Execute each as a small addendum pass — no plan
or design-review cycle: make the change, run `make all` (plus `make
markdownlint`/`make nixie` for any Markdown), `coderabbit review --agent`,
commit, and tick the matching roadmap sub-task on merge. The substantial,
cross-cutting follow-ups raised against this task (single-sourcing the
contract-guard helpers, renaming the now document-generic scanner module,
auditing guard keyword/anchor brittleness, and guarding the developers'-guide
exit-3 formatter-count prose) were re-routed to roadmap step 7.6; this is the
small coverage gap.

- [x] 6.3.9.1 — Cover the trailing-comma discard branch of
  `extract_brace_field_list` (from review:6.3.9 / audit:6.3.9, low; two
  near-identical proposals merged). The scanner helper documents that empty
  comma-split fragments (e.g. a trailing comma) are discarded via the `if
  field:` guard at `tests/_skill_contract_scanner.py:268`, and the behaviour is
  correct, but no unit test exercises that branch, so a regression removing the
  guard would pass every current test. Add one unit case planting `{a, b, }` and
  asserting it parses to `[a, b]`, pinning the documented contract and closing
  the coverage gap. Gate with `make all`.
