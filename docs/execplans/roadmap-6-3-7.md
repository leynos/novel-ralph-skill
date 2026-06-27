# Pin the SKILL.md command-contract restatement to the code with a drift-guard test

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: COMPLETE (implemented round 2)

## Purpose / big picture

Roadmap task 6.3.7 closes the last unguarded copy of the shared interface
contract. After roadmap task 6.3.3, the contract — the disambiguated exit-code
table (design §3.2) and the six-field JSON envelope skeleton (design §3.1) — is
restated in four places: `docs/adr-003-shared-interface-contract.md` (Table 2),
the harness design (`docs/novel-ralph-harness-design.md` §3.1 envelope and §3.2
exit codes), the developers' guide, and the agent-facing skill
(`skill/novel-ralph/SKILL.md`). Three of these are either the canonical source
or already pinned; the `SKILL.md` exit-code table and envelope skeleton are the
one copy that no test pins. A change to the
`ExitCode` enum, the envelope field set, or `ENVELOPE_SCHEMA_VERSION` would
silently stale the table the dogfooding agent reads — the exact per-command
drift that roadmap step §6.3 exists to close.

After this change, a developer who edits `novel_ralph_skill/contract/exit_codes.py`,
`novel_ralph_skill/contract/envelope.py`, or the `SKILL.md` restatement without
keeping them in lockstep gets a failing test naming the divergence, rather than
discovering the staleness in production. Success is observable by running the
new test before the change (it fails on a planted divergence) and after (it
passes against the live `SKILL.md`), and by running `make all`,
`make markdownlint`, and `make nixie` green.

The mechanism is a docs-level drift-guard, following the repository's
established in-process prose-guard pattern (the `read_repo_text` fixture, no
subprocess, no `novel_ralph_skill` runtime behaviour). It reads `SKILL.md`,
extracts the exit-code table rows and the envelope skeleton, and asserts each
cell matches the live `ExitCode` enum, the live `Envelope` field set and order,
`ENVELOPE_SCHEMA_VERSION`, and the canonical ADR-003 Table 2 / design §3.1
copies. The guard is mechanical, so it does not rely on reviewer diligence.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Work exclusively inside the git-donkey worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-7`. Never
  read-modify-write any file in the root/control worktree.
- This is a test-and-docs task. Do **not** modify production source under
  `novel_ralph_skill/` (in particular `contract/exit_codes.py`,
  `contract/envelope.py`, `commands/names.py`). The guard reads them; it must
  not change them. The roadmap success criterion is a guard, not a contract
  change.
- Do not change the *content* of `SKILL.md`'s exit-code table, envelope
  skeleton, or field bullets, nor of ADR-003 Table 2 or design §3.1. The guard
  pins the existing restatement; it is not a licence to re-edit the contract.
  The only permitted `SKILL.md` edit, if the guard's anchors demand it, is a
  whitespace-neutral clarification that does not change a documented value, and
  any such edit must be recorded in the Decision Log with its justification.
- The new test must keep the repository's prose-guard discipline: it reads
  `SKILL.md` in process through the shared `read_repo_text` fixture
  (`tests/conftest.py`), does **not** shell out, and does **not** import
  `novel_ralph_skill` for its *runtime* side effects. It may import the
  contract *constants and enum* (`ExitCode`, `Envelope` dataclass fields,
  `ENVELOPE_SCHEMA_VERSION`) — these are pure data, and importing them is what
  ties the guard to the code source the roadmap names. This mirrors
  `tests/test_contract_envelope_snapshots.py`, which already imports the
  contract module directly.
- Keep the new test module under the 400-line cap the repository applies to
  test modules (see `tests/test_skill_deflation_guard.py` and
  `tests/test_state_layout_reference.py`, which extracted helpers to stay under
  it). Extract any non-trivial parsing helper into a sibling `tests/_*.py`
  module of pure functions, as `tests/_state_layout_scanner.py` does.
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments,
  docstrings, and the commit message. 100% docstring coverage is enforced by
  `make lint`; every new module, class, function, and fixture needs a
  docstring.
- The integration branch is `main`; treat `origin/main` as canonical. Each work
  item is independently committable and must pass the full gate before commit.

## Tolerances (exception triggers)

- Scope: if implementation requires net changes to more than 3 files or more
  than 350 lines of code, stop and escalate. (Expected surface: one new test
  module, optionally one extracted helper module, and possibly a one-line
  test-discovery inventory update.)
- Interface: if pinning the contract requires changing any public API signature
  in `novel_ralph_skill/contract/`, stop and escalate — that would mean the
  guard cannot read the contract as data, which contradicts the task framing.
- Source divergence: if the guard reveals that `SKILL.md` already diverges from
  the live contract (a real, pre-existing drift rather than a planted one),
  stop and escalate. Fixing a live drift is a contract edit outside this task's
  scope; record it in the Decision Log and surface it.
- Dependencies: if a new external dependency is required, stop and escalate. No
  new dependency is expected; `syrupy` (snapshots), `pytest`, and `hypothesis`
  are already in the test toolchain.
- Iterations: if the new test still fails against the live, unplanted `SKILL.md`
  after 3 attempts to correct the *guard* (not the contract), stop and
  escalate.
- Ambiguity: if a load-bearing behavioural claim cannot be verified against the
  code or a cited document, stop and present options rather than guessing.

## Risks

    - Risk: Brittleness — a guard that pins whole sentences or exact table
      whitespace churns on every benign re-wording of SKILL.md.
      Severity: medium
      Likelihood: medium
      Mitigation: Pin semantic cells, not prose. Parse the exit-code table into
      (code, meaning-keyword, response-keyword) triples and assert the *set of
      codes* {0,1,2,3,4} and a small stable keyword per cell (e.g. "success",
      "benign", "usage", "state", "actionable"/"finding"), exactly as
      test_skill_deflation_guard.py pins mechanism substrings rather than whole
      sentences. For the envelope, parse the fenced JSON block and assert the
      *field set and order*, plus the schema_version *value*, not the surrounding
      prose.

    - Risk: The SKILL envelope skeleton intentionally differs from design §3.1
      in one field value: SKILL.md shows "working_dir": "working" (the literal
      token) while design §3.1 shows an absolute resolved path
      "/home/me/my-novel/working" (roadmap §6.3.4 surfaced the resolved path).
      A naive value-equality guard between the two skeletons would false-fail.
      Severity: medium
      Likelihood: high
      Mitigation: Pin the field *set and order* (command, schema_version, ok,
      working_dir, result, messages) across both skeletons, and pin
      schema_version's *value* (1) against ENVELOPE_SCHEMA_VERSION. Do NOT pin
      working_dir's example *value* across documents. Record this carve-out
      explicitly in the Decision Log and in the test docstring so a future
      reader does not "tighten" it back into a false failure. The carve-out is
      verified below against the two source files.

    - Risk: The guard imports the contract module, coupling a docs test to
      production code import-time behaviour.
      Severity: low
      Likelihood: low
      Mitigation: The contract module (envelope.py, exit_codes.py) is pure data
      and side-effect-free at import (verified: no top-level I/O, only enum and
      dataclass definitions). test_contract_envelope_snapshots.py already
      imports it. Importing ExitCode and the Envelope dataclass fields is the
      *point* — it ties the SKILL table to the code, satisfying the roadmap's
      "or from the ExitCode, envelope-field, and schema_version source" clause.

    - Risk: Markdown-table parsing is fiddly (leading/trailing pipes, alignment
      rows, padding spaces).
      Severity: low
      Likelihood: medium
      Mitigation: Extract a small pure parser (`_skill_contract_scanner.py`)
      with its own focused unit tests over planted fixtures, mirroring how
      `tests/_state_layout_scanner.py` is unit-tested by
      `tests/test_state_layout_reference.py`. Strip cells and skip the
      alignment (`----`) row.

    - Risk: The drift-guard could pass vacuously if a heading/fence anchor is
      renamed and the region comes back empty.
      Severity: medium
      Likelihood: low
      Mitigation: Follow the deflation-guard's `_require_index` / `_slice_between`
      discipline — every anchor lookup asserts presence and fails loudly when an
      anchor is missing, so a renamed "### Exit-code table" heading or removed
      JSON fence fails rather than silently passing.

    - Risk: (B1, round-1 blocker) The design doc carries TWO ```json fences.
      The §3.1 six-field envelope skeleton is at line 146 (fields command,
      schema_version, ok, working_dir, result, messages); a SECOND fence at line
      365 is a `novel done` example that OMITS working_dir (five fields:
      command, schema_version, ok, result, messages). An extractor that pulls
      "the first json fence in the file", or that bounds the design region too
      loosely, will read the line-365 example and false-fail (5 keys vs SKILL's
      6). A contributor would then "fix" the false-fail by loosening the order
      assertion, silently killing the coupling (Doggylump pre-mortem).
      Severity: high
      Likelihood: high (if unaddressed)
      Mitigation: Slice the design region to §3.1 BEFORE extracting any fence:
      `_slice_doc_region(design_text, "### 3.1", "### 3.2")` (heading 137 → 212,
      verified below), then extract the FIRST ```json fence within that slice
      (line 146). Add a positive assertion that the extracted design skeleton
      contains `working_dir`, so a future doc reshuffle that pulls the wrong
      fence fails loudly rather than silently. Extend the non-vacuous region
      test to the design slice (assert it contains `"working_dir"`).

    - Risk: (B2, round-1 blocker) The three exit-code tables differ in column
      count, so a fixed two-non-code-cell extractor mis-reads one of them.
      ADR-003 Table 2 = 3 cols (Code, Meaning, Harness response); design §3.2 =
      4 cols (Code, Meaning, Harness response, Example); SKILL.md = 3 cols (Code,
      Meaning, Agent response). The original `extract_exit_code_rows(rows) ->
      dict[int, tuple[str, str]]` assumes exactly two non-code cells and shifts
      by one on design §3.2's four-column rows (the Example column), an
      off-by-one trap. The Meaning *wording* also differs across tables (SKILL:
      "Usage error; the invocation is wrong" vs ADR: "Usage error"), so even the
      Meaning cell cannot be compared by exact string.
      Severity: high
      Likelihood: high (if unaddressed)
      Mitigation: Key the integer code (column 0) to the Meaning cell (column 1)
      ONLY — `extract_exit_code_meanings(rows) -> dict[int, str]` — and ignore
      every column after the first two, making the extractor column-count
      tolerant. State explicitly that only the Meaning column is load-bearing
      across the three tables, and compare it by per-code keyword presence (not
      exact string), since the Meaning wording diverges by table.

## Progress

    - [x] Work item 1: Add a failing drift-guard skeleton and red-test proof
      (folded into Work item 2's commit to keep every commit gate-green).
    - [x] Work item 2: Implement the exit-code-table drift guard against
      ExitCode and ADR-003 Table 2 / design §3.2, comparing per-code Meaning
      keywords (column 1 only, column-count tolerant — B2).
    - [x] Work item 3: Implement the envelope-skeleton drift guard against the
      Envelope field set/order, ENVELOPE_SCHEMA_VERSION, and design §3.1, with
      the design fence sliced to the §3.1 region and a working_dir-present
      assertion (B1).
    - [x] Work item 4: Harden against vacuous-pass (including the design §3.1
      slice), add the planted-divergence red/green proof, and finalise docs
      validation. No inventory update (B3).

## Surprises & discoveries

    - The scanner module `tests/_skill_contract_scanner.py` is NOT matched by
      the `**/test_*.py` Ruff per-file-ignores (pyproject.toml), so it carries
      no PLR2004 carve-out: the `len(cells) < 2` minimum-column comparison
      tripped `magic-value-comparison` and was lifted into the
      `_MIN_CODE_ROW_CELLS` constant. The guard module itself, being
      `test_*.py`, keeps the bare-assert and magic-value allowances.
    - `make markdownlint` globs every markdown file, including the untracked
      planning artifact `docs/execplans/roadmap-6-3-7.logisphere-review-r1.md`,
      which carries pre-existing MD013/MD038 errors from the planning phase.
      That artifact is outside this task's commit surface (only the execplan and
      the two test files are committed); the execplan itself lints clean
      (`markdownlint-cli2 docs/execplans/roadmap-6-3-7.md` → 0 errors). Recorded
      in Open issues for the orchestrator's awareness; no code/docs this task
      touches fails the markdown gate.
    - CodeRabbit (WI2 run) flagged two second-person/first-person pronoun
      breaches in this execplan's prose (the "You can observe success" sentence
      and the "I therefore scope it out" Decision-Log rationale); both were
      rewritten to impersonal form to honour the docs pronoun rule.
    - `make fmt` (mdformat-all) reflows EVERY tracked markdown file in the repo,
      not just the changed ones, and the wholesale reflow then trips
      pre-existing MD013 line-length errors in unrelated `docs/issues/audit-*.md`
      files. This confirms the plan's deliberate omission of `make fmt` from the
      per-item gate: running it here mutated 255 unrelated docs. The churn was
      parked in a `git stash` ("spurious make-fmt mdformat churn … (to
      discard)") and the staged guard edit kept via `--keep-index`, matching the
      recurring discard pattern visible in the worktree's stash list. CodeRabbit
      WI3 raised a finding asking the plan to add `make fmt`; it is recorded here
      and NOT actioned in the plan body, because doing so would prescribe a
      repo-wide reformat that is out of scope and destructive (Tolerances:
      scope).
    - CodeRabbit's WI3 and WI4 runs raised findings only against the parked
      planning artifacts `roadmap-6-3-7.logisphere-review-r1.md` and `-r2.md`
      (stale helper names, a §3.1/§3.2 label slip, the `make fmt` request).
      Those review files are planning scaffolding, not part of this task's
      commit surface, and were stashed out of the working tree; no finding
      touched the committed test files or this execplan. Recorded here and in
      Open issues; no code change warranted.

## Decision log

    - Decision: cuprum and other locked external libraries (Cyclopts,
      pytest-timeout, uv) are NOT load-bearing for this task; the plan uses none
      of them.
      Rationale: The roadmap success criterion is a docs-level drift-guard that
      reads SKILL.md text in process and compares it against the in-repo
      ExitCode/Envelope/ENVELOPE_SCHEMA_VERSION constants. It runs no
      subprocess, builds no command catalogue, and executes no installed binary.
      The repository's established prose-guard tests this plan copies
      (tests/test_skill_deflation_guard.py, tests/test_state_layout_reference.py)
      read files through the read_repo_text fixture with no cuprum, no Cyclopts,
      and no uv. The contract-source coupling is a plain Python import of pure
      data (verified: envelope.py and exit_codes.py do no I/O at import), exactly
      as tests/test_contract_envelope_snapshots.py already does. Pinning a cuprum
      API here would be a justification for a mechanism the task does not use; it
      is therefore scoped out explicitly rather than hedged.
      Date/Author: 2026-06-26, planner

    - Decision: Pin field *set and order* across the SKILL and design envelope
      skeletons but NOT the working_dir example *value*.
      Rationale: Verified divergence — SKILL.md line 133 carries
      `"working_dir": "working"` whereas design §3.1 line 151 carries
      `"working_dir": "/home/me/my-novel/working"`. Both are deliberate: SKILL's
      restatement uses the literal token, design surfaces the resolved absolute
      path (roadmap §6.3.4, design §3.1 bullet at lines 158-166). The
      load-bearing contract is the field set/order and schema_version, which the
      guard pins; working_dir's example string is presentational and must be left
      free.
      Date/Author: 2026-06-26, planner

    - Decision: (B1 fix) Anchor the design-side envelope fence to the §3.1 slice
      (`### 3.1` → `### 3.2`) before extracting, and assert `working_dir`
      present in the extracted design skeleton.
      Rationale: Verified two ```json fences in
      `docs/novel-ralph-harness-design.md`: the §3.1 skeleton at line 146 (six
      fields, with working_dir) and a `novel done` example at line 365 (five
      fields, OMITTING working_dir). The §3.1 heading is at line 137 and §3.2 at
      line 212, so the slice (137→212) contains only the line-146 fence.
      Extracting the first fence in that slice deterministically picks the
      six-field skeleton; the `working_dir`-present assertion makes a future
      reshuffle that pulls the five-field example fail loudly. Without the slice,
      the guard would compare SKILL's 6 keys against design's 5 and false-fail.
      Date/Author: 2026-06-26, planner

    - Decision: (B2 fix) The exit-row extractor keys code (column 0) to the
      Meaning cell (column 1) only — `dict[int, str]` — and is column-count
      tolerant; only the Meaning column is cross-table load-bearing, compared by
      keyword presence not exact string.
      Rationale: Verified the three tables differ in column count (ADR-003 = 3,
      design §3.2 = 4, SKILL = 3) and in Meaning wording (SKILL "Usage error;
      the invocation is wrong" vs ADR/design "Usage error"; SKILL "Actionable
      finding a detector surfaced" vs ADR/design "Actionable findings requiring
      agent intervention"). A two-non-code-cell tuple shifts on design's
      four-column rows, and exact Meaning equality would false-fail on the
      benign wording differences. Keying to column 1 and matching per-code
      keywords (success/benign/usage/state/actionable|finding) is the only
      mechanism that survives all three tables. The Harness-response / Agent-
      response / Example columns are presentational and deliberately left free.
      Date/Author: 2026-06-26, planner

    - Decision: (B3 fix) Remove the WI4 `_KNOWN_SKILL_MARKDOWN` coupling
      entirely; it can never reference a `tests/` module, and there is no
      test-collection-count guard to update.
      Rationale: Traced `_KNOWN_SKILL_MARKDOWN` in
      `tests/test_state_layout_reference.py` (lines 55-64): it is a frozenset of
      eight markdown DOCUMENTS under `skill/novel-ralph/`, paired with
      `test_discovery_covers_known_skill_files` (line 351), which globs
      `skill/novel-ralph/**/*.md`. A new test module under `tests/` is outside
      that glob and can never appear in the inventory, so the original "if it
      references the new test module, update it" step was dead. Separately
      searched the whole `tests/` tree for any global collected-test-module-count
      assertion, `tests/`-directory inventory frozenset, or `pytest_collect*` /
      `pytest_collection*` hook: NONE exists. The only `tests/` references are a
      directory-existence check (`tests/test_conftest_helpers.py` line 29) and a
      docstring note in `tests/test_per_chapter_loop_bdd.py`; all `rglob`/glob
      calls in the suite scan working/manuscript/tmp_path fixtures, not the test
      tree. Adding `tests/test_skill_contract_drift_guard.py` (and an optional
      sibling `tests/_skill_contract_scanner.py`) therefore breaks no commit
      gate via a collection tripwire. WI4 no longer touches any inventory.
      Date/Author: 2026-06-26, planner

    - Decision: (Calibration, Wafflecat alternative) Keep BOTH the code-coupling
      and the ADR-003/design cross-document checks; do not reduce to code-only.
      Rationale: The roadmap success criterion explicitly requires the guard to
      fail if SKILL diverges "from ADR-003 Table 2 / design §3.1 OR from the
      ExitCode, envelope-field, and schema_version source" — the ADR/design
      agreement is named, not optional. The Purpose paragraph's "three of these
      are already pinned" refers to the canonical/source status of ADR-003 and
      the code, not to an existing SKILL↔ADR or SKILL↔design cross-guard; this
      task adds the first such cross-guard, so dropping it would under-deliver
      the clause. With B1 (design slice) and B2 (Meaning-only, keyword) fixed,
      the cross-document parser surface is small and safe, so the belt-and-braces
      cost is low and the roadmap clause is met directly.
      Date/Author: 2026-06-26, planner

    - Decision: Use a generalised doc-region slice helper for cross-document
      slicing rather than the deflation guard's `_slice_between` verbatim.
      Rationale: `tests/test_skill_deflation_guard.py` `_slice_between` (lines
      63-78) hard-codes "SKILL.md" in its assertion messages and is private to
      that module. Re-using it across two other files (the design doc and
      ADR-003) would emit misleading "not found in SKILL.md" errors. The
      extracted scanner therefore defines `slice_doc_region(text, start, end,
      *, source)` with a `source` label in its failure message, preserving the
      loud-failure discipline while naming the correct file.
      Date/Author: 2026-06-26, planner

## Outcomes & retrospective

    - Delivered as three commits (work item 1 folded into work item 2): the
      exit-code-table guard, the envelope-skeleton guard, and the vacuous-pass
      hardening with the planted-divergence proof. The change surface is two
      test files — `tests/_skill_contract_scanner.py` (pure parser) and
      `tests/test_skill_contract_drift_guard.py` (the guard, 400 lines, at the
      cap) — plus this execplan. No production source under `novel_ralph_skill/`
      and no `SKILL.md` content changed (the only `SKILL.md` edits were the
      transient, reverted red-test plants).
    - The guard passes against the live `SKILL.md`, ADR-003 Table 2, design §3.1
      and §3.2, and proved genuinely red on both planted divergences (see
      Artifacts and notes). The full suite is 1332 passed, 1 skipped under
      `make all`.
    - Two carve-outs held as designed: the Meaning column is compared by per-code
      keyword (the three tables' wording genuinely differs), and `working_dir`'s
      example value is left free (SKILL's `"working"` vs design's absolute path).
      Neither false-failed.
    - Retrospective note: `make fmt` is a repo-wide mdformat reflow and must not
      be run as a per-item gate; it rewrites hundreds of unrelated docs and
      surfaces pre-existing MD013 errors. The plan's quartet (`make all`,
      `make markdownlint`, `make nixie`) is the correct per-item docs gate.

## Context and orientation

This repository is a Python skill (`skill/novel-ralph/`) plus its supporting
package (`novel_ralph_skill/`) and a `tests/` tree. The shared interface
contract — how every `novel` command reports to the harness — is defined once
and restated in several reader-facing documents.

The canonical contract sources, by full path:

- `novel_ralph_skill/contract/exit_codes.py` defines
  `class ExitCode(enum.IntEnum)` with members `SUCCESS = 0`,
  `BENIGN_NEGATIVE = 1`, `USAGE_ERROR = 2`, `STATE_ERROR = 3`,
  `ACTIONABLE_FINDING = 4`, and `is_ok(code)` (the `ok` biconditional). This is
  the code source of the exit-code vocabulary.
- `novel_ralph_skill/contract/envelope.py` defines
  `ENVELOPE_SCHEMA_VERSION: int = 1` and the frozen `Envelope` dataclass whose
  fields, in order, are `command`, `schema_version`, `ok`, `working_dir`,
  `result`, `messages`. `render_machine` builds the JSON in that exact order.
  This is the code source of the envelope field set, order, and schema version.

The four restatement sites, by full path:

- `docs/adr-003-shared-interface-contract.md` — Table 2 (the markdown table at
  lines 90-96, three columns: Code, Meaning, Harness response) is the exit-code
  policy; the `result`/`messages`/`schema_version` prose (lines 100-106) defines
  the envelope semantics. This ADR is the documented source of truth the SKILL
  section names.
- `docs/novel-ralph-harness-design.md` §3.1 "Output modes" (heading at line 137)
  carries the six-field envelope skeleton at lines 146-155 (the FIRST ```json
  fence; a SECOND, five-field `novel done` example lives at line 365, in §4, and
  must be excluded — see B1). §3.2 "Exit codes" (heading at line 212) carries
  the exit-code table at lines 221-227 (FOUR columns: Code, Meaning, Harness
  response, Example). The §3.1 region runs from its heading (line 137) to the
  §3.2 heading (line 212).
- `docs/developers-guide.md` — the "The shared JSON envelope" and
  "Disambiguated exit codes" sections (already the developer-facing single
  source SKILL points at; not re-pinned here beyond cross-reference).
- `skill/novel-ralph/SKILL.md` — the "## Command contract" section (heading at
  line 90): the "### Exit-code table" heading at line 102 with its markdown
  table at lines 107-113 (three columns: Code, Meaning, Agent response), the
  "### Envelope schema" heading at line 123 with its fenced JSON skeleton at
  lines 128-137, and the field bullets at lines 139-150. The envelope region
  ends at the "### Invocation discipline" heading (line 155). **This is the one
  copy no test pins.** All anchoring is by heading text, not line number; the
  line numbers above are orientation only and may drift.

The established prose-guard pattern this plan copies:

- `tests/test_skill_deflation_guard.py` reads `SKILL.md` through the
  `read_repo_text` fixture, slices it into regions by heading offsets with
  `_slice_between` / `_require_index` (which fail loudly on a missing anchor),
  and asserts small stable *mechanism* substrings within each region.
- `tests/test_state_layout_reference.py` + `tests/_state_layout_scanner.py`
  show the helper-extraction discipline: a pure scanner module of functions over
  markdown text, unit-tested by the guard module, keeping each file under the
  400-line cap.
- `tests/test_contract_envelope_snapshots.py` shows that importing the contract
  module (`ExitCode`, `build_envelope`, `render_machine`) directly from a test
  is the sanctioned way to tie a test to the code, and that `working_dir` is
  normalised to the literal `"working"` token for snapshotting.

The shared fixture: `tests/conftest.py` defines `read_repo_text` (an in-process
repo-relative UTF-8 reader) and the `RepoTextReader` protocol; `project_root`
gives the worktree root. These are the only scaffolding the guard needs.

Term definitions:

- *Drift-guard*: a test that fails when two copies of the same fact (here, the
  SKILL restatement and the code/canonical source) diverge.
- *Prose-guard*: the repository's name for an in-process test that reads a
  documentation file as text and asserts mechanical properties of it without
  shelling out.
- *Envelope skeleton*: the fenced JSON object showing the six envelope fields in
  contract order.

## Plan of work

The work proceeds red-first (a failing skeleton), then builds the two guard
halves (exit-code table, envelope skeleton), then hardens against vacuous
passes and proves red/green on a planted divergence. Each work item is a single
commit that passes `make all`, `make markdownlint`, and `make nixie`.

Decision before writing code (resolved, no fork): the guard lives in a new
module `tests/test_skill_contract_drift_guard.py`, with table/JSON parsing
helpers in a sibling pure module `tests/_skill_contract_scanner.py` so both
files stay under the 400-line cap and the parser is independently unit-tested.
This mirrors the `test_state_layout_reference.py` + `_state_layout_scanner.py`
split exactly. (If, while implementing, the guard module lands comfortably under
~300 lines including parsing, the parser may stay inline; record that choice in
the Decision Log. The default is extraction.)

- Stage A (Work item 1): scaffolding and a red test.
- Stage B (Work items 2-3): the two guard halves.
- Stage C (Work item 4): vacuous-pass hardening, planted-divergence red/green
  proof, and final docs gates.

Each stage ends with `make all`. Do not proceed to the next stage on a red gate.

## Concrete steps

All commands run from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-7`.

### Work item 1 — Failing drift-guard skeleton (Stage A)

Implements: the roadmap 6.3.7 success criterion ("a drift-guard test fails if
the SKILL.md exit-code table or envelope skeleton diverges … the guard reuses
the repo's established prose-guard pattern"); AGENTS.md "Establish a failing
test suite prior to implementation (red, green, refactor)".

Docs to read first: `docs/roadmap.md` task 6.3.7 (lines 2278-2301); the
execplans skill (red-green-refactor, mandatory living sections); AGENTS.md
testing rules (lines 143-172).

Skills to load: `python-router` (route to `python-testing` for the pytest
fixture/parametrize idiom; `python-types-and-apis` for the `RepoTextReader`
protocol import). Load `leta` first for navigation; use `sem` for history.

Create `tests/test_skill_contract_drift_guard.py` with:

- A module docstring stating it pins the `SKILL.md` command-contract restatement
  (the "## Command contract" exit-code table and envelope skeleton) to
  `ExitCode`, the `Envelope` field set, and `ENVELOPE_SCHEMA_VERSION`, following
  the prose-guard pattern of `test_skill_deflation_guard.py`, and naming the
  working_dir example-value carve-out (Decision Log).
- A `_SKILL_PARTS = ("skill", "novel-ralph", "SKILL.md")` constant and a
  `skill_text` fixture over `read_repo_text`, copied from the deflation guard.
- One *placeholder* assertion that intentionally fails (e.g. asserting a
  sentinel the file does not contain), so the suite is red before the guard
  exists.

Run the new module and confirm it is collected and red:

    uv run pytest -q tests/test_skill_contract_drift_guard.py

Expected: 1 failed (the placeholder), 0 errors (the module imports and the
fixture resolves). Then run the gate:

    make all

Expected: the only failure is the planted placeholder in the new module. Commit
is deferred until the placeholder is replaced; if committing this stage, replace
the placeholder with an xfail-marked stub so the gate is green — record the
choice in the Decision Log. Preferred path: fold Work item 1 into Work item 2's
commit so no broken commit lands. (Decision recorded below: ship Work items 1+2
as one commit to keep every commit gate-green.)

### Work item 2 — Exit-code-table drift guard (Stage B)

Implements: roadmap 6.3.7 ("fails if the SKILL.md exit-code table … diverges
from ADR-003 Table 2 / design §3.2 or from the ExitCode … source");
ADR-003 Table 2 (`docs/adr-003-shared-interface-contract.md` table at lines
90-96, three columns); design §3.2 (`docs/novel-ralph-harness-design.md` table
at lines 221-227, four columns); `novel_ralph_skill/contract/exit_codes.py`.

Docs to read first: ADR-003 Table 2 and the surrounding "Decision outcome"
prose (lines 86-106); design §3.2 (heading line 212, table 221-227 — note the
fourth "Example" column); SKILL.md "### Exit-code table" (heading line 102,
table 107-113). Skills: `python-router` → `python-testing`;
`python-iterators-and-generators` if a table parser uses generators.

If extracting (default), create `tests/_skill_contract_scanner.py` with pure
functions:

- `parse_markdown_table(region: str) -> list[tuple[str, ...]]` — splits a
  GitHub-flavoured markdown table region into stripped cell tuples, skipping the
  header separator (`---`) row. Docstring explains it tolerates optional leading
  and trailing pipes and collapses padding whitespace, and that each returned
  tuple has the column count of its source table (which differs by table).
- `extract_exit_code_meanings(rows: list[tuple[str, ...]]) -> dict[int, str]` —
  maps each numeric code (column 0) to its Meaning cell (column 1) ONLY, ignoring
  every later column. **B2 fix**: this replaces the round-1
  `extract_exit_code_rows -> dict[int, tuple[str, str]]`, which assumed exactly
  two non-code cells and shifted by one on design §3.2's four-column rows. The
  docstring states explicitly that only the Meaning column is load-bearing across
  the three tables (column counts: ADR-003 = 3, design §3.2 = 4, SKILL = 3), and
  that the extractor is column-count tolerant: it reads columns 0 and 1 and
  discards the rest. Rows whose column-0 cell is not an integer (e.g. a stray
  blank line) are skipped, so a malformed region cannot silently corrupt the map.
- `slice_doc_region(text: str, start: str, end: str, *, source: str) -> str` —
  the generalised, source-labelled region slicer (Decision Log). Mirrors the
  deflation guard's `_slice_between` (loud failure when either anchor is missing)
  but names `source` in the message, so a missing `### 3.2` in the design doc
  does not report "not found in SKILL.md".

In `tests/test_skill_contract_drift_guard.py` add:

- A `_EXIT_TABLE_HEADING = "### Exit-code table"` anchor and an
  `_ENVELOPE_HEADING = "### Envelope schema"` anchor; an `exit_table_region`
  fixture slicing SKILL.md between them via `slice_doc_region(skill_text,
  _EXIT_TABLE_HEADING, _ENVELOPE_HEADING, source="SKILL.md")`.
- `_CODE_KEYWORDS: dict[ExitCode, tuple[str, ...]]` derived from the enum:
  `SUCCESS → ("success",)`, `BENIGN_NEGATIVE → ("benign",)`,
  `USAGE_ERROR → ("usage",)`, `STATE_ERROR → ("state",)`,
  `ACTIONABLE_FINDING → ("actionable", "finding")`. Keying off the enum member,
  not a string copied from SKILL, is the load-bearing coupling.
- `test_skill_exit_codes_cover_exactly_the_enum`: parse SKILL's table with
  `parse_markdown_table` + `extract_exit_code_meanings`, assert the set of
  integer codes equals `{c.value for c in ExitCode}` (i.e. `{0,1,2,3,4}`).
  Adding or removing an enum member without updating the table fails here.
- `test_skill_exit_code_meanings_match_keywords`: for each `ExitCode`, assert at
  least one of its `_CODE_KEYWORDS` appears (case-insensitively) in SKILL's
  Meaning cell for that code. Pin keywords, not whole sentences (Risks:
  brittleness).
- `test_skill_exit_table_agrees_with_adr003_and_design`: read ADR-003 Table 2
  (slice between "Adopt Option A. The exit-code table is:" / `_Table 2:` anchors,
  or the heading `## Decision outcome` to the next `_Table`) and design §3.2's
  table (slice via `slice_doc_region(design_text, "### 3.2", "### 3.3",
  source="design")`) through `read_repo_text`, parse both with
  `extract_exit_code_meanings`, and assert that for every `ExitCode` the Meaning
  cell in each document contains the same per-code keyword as SKILL's. **B2 fix**:
  compare by per-code keyword presence, NOT exact Meaning string — verified that
  the wording differs across tables (SKILL "Usage error; the invocation is wrong"
  vs ADR/design "Usage error"; SKILL "Actionable finding a detector surfaced" vs
  ADR/design "Actionable findings requiring agent intervention"). This pins the
  "matches ADR-003 Table 2 / design §3.2" clause against the canonical
  *documents*, complementing the enum coupling above, and survives the
  four-column design table because only columns 0 and 1 are read.

Tests to add/update (per AGENTS.md): the above are unit/prose-guard tests in
`tests/`. If `tests/_skill_contract_scanner.py` is created, add a small unit
test class `TestSkillContractScanner` in the guard module that drives the parser
over a *planted* in-string table fixture (a multi-line literal, not a file) to
prove it skips the separator row, tolerates padding, and rejects a malformed
row — mirroring how `test_state_layout_reference.py` unit-tests its scanner with
planted recipes. No snapshot test is warranted here: the guard asserts
semantic equality, and AGENTS.md says to avoid snapshot-only coverage for logic
assertable directly. No property test is warranted: there is no
generative-input surface — the inputs are three fixed in-repo documents.

Validation:

    uv run pytest -q tests/test_skill_contract_drift_guard.py
    make all

Expected: all new tests pass; full suite green. Then, because SKILL.md is
markdown (no change to it in this item):

    make markdownlint
    make nixie

Expected: both green (no markdown changed, but run them to confirm the gate).
Commit this work item (folding in Work item 1's scaffolding) with a message
referencing roadmap 6.3.7.

### Work item 3 — Envelope-skeleton drift guard (Stage B)

Implements: roadmap 6.3.7 ("fails if the SKILL.md … envelope skeleton diverges
from … design §3.1 or from the … envelope-field, and schema_version source");
design §3.1 (`docs/novel-ralph-harness-design.md` heading line 137, skeleton at
146-155); `novel_ralph_skill/contract/envelope.py` (the `Envelope` dataclass
fields and `ENVELOPE_SCHEMA_VERSION`).

Docs to read first: design §3.1 (heading 137; note the working_dir
absolute-path bullet, lines 158-166; note the SECOND, five-field ```json
example at line 365 in §4 — B1); SKILL.md "### Envelope schema" (heading line
123, skeleton 128-137, bullets 139-150); `envelope.py` (field order in the
dataclass and in `render_machine`). Skills: `python-router` →
`python-testing`, `python-data-shapes` (dataclass field introspection via
`dataclasses.fields`).

Add to `tests/test_skill_contract_drift_guard.py` (and the scanner module if
extracting):

- `extract_fenced_json(region: str, fence_lang: str = "json") -> str` in the
  scanner — pulls the FIRST ```` ```json ```` fenced block out of the region it
  is given, failing loudly if absent (vacuous-pass guard). Because it operates on
  whatever region the caller passes, the caller MUST narrow the design text to
  the §3.1 slice first (see the design fixture below); otherwise the file-level
  first fence is still the §3.1 one, but a region passed too wide risks pulling
  the wrong fence — B1.
- An `_ENVELOPE_END = "### Invocation discipline"` anchor and an `envelope_region`
  fixture: `slice_doc_region(skill_text, _ENVELOPE_HEADING, _ENVELOPE_END,
  source="SKILL.md")`, capturing the skeleton (128-137) AND the field bullets
  (139-150) up to the next H3. (Verified: `### Invocation discipline` is the next
  H3, at line 155.)
- A `_DESIGN_PARTS = ("docs", "novel-ralph-harness-design.md")` constant and a
  `design_envelope_skeleton` fixture: read the design doc, slice it to the §3.1
  region with `slice_doc_region(design_text, "### 3.1", "### 3.2",
  source="novel-ralph-harness-design.md")` (heading 137 → 212, verified), then
  `extract_fenced_json` the first fence WITHIN that slice (line 146). **B1 fix**:
  this is the explicit design-side region bound the round-1 plan omitted; it
  excludes the line-365 five-field `novel done` example in §4. The fixture
  asserts `"working_dir" in skeleton` before returning, so a future doc reshuffle
  that pulls the five-field example (or drops working_dir) fails loudly here
  rather than silently false-failing the order comparison downstream.
- `test_skill_envelope_fields_match_dataclass`: parse the SKILL fenced JSON,
  assert `list(parsed.keys())` equals
  `[f.name for f in dataclasses.fields(Envelope)]` — i.e.
  `["command", "schema_version", "ok", "working_dir", "result", "messages"]`.
  This pins the field set **and order** to the code (the contract field order is
  load-bearing; `render_machine` asserts it too).
- `test_skill_envelope_schema_version_matches_constant`: assert the parsed
  `schema_version` value equals `ENVELOPE_SCHEMA_VERSION` (1). This is the
  `schema_version` coupling named in the success criterion.
- `test_skill_envelope_matches_design_field_order`: parse the
  `design_envelope_skeleton` (the §3.1-sliced fence) and assert its key order
  equals SKILL's key order. Per the Decision Log carve-out, assert key
  *order/set* only — do **not** assert `working_dir`'s example value (SKILL's
  `"working"` vs design's absolute path), and document that carve-out in the
  test docstring. **B1 fix**: also assert `"working_dir" in design_keys`
  positively, so the test fails loudly (not silently 5-vs-6) if the design region
  ever yields the working_dir-less example.
- `test_skill_envelope_bullets_name_every_field`: assert each of the six field
  names appears as a documented bullet in the envelope region (the
  `- \`command\` …` bullets, 139-150), so a field added to the skeleton without
  prose, or prose left behind after a field removal, fails. Keyword presence, not
  sentence text.

Tests to add (per AGENTS.md): unit/prose-guard tests as above. Extend
`TestSkillContractScanner` with planted fixtures proving (a) `extract_fenced_json`
returns the block and raises on a missing fence, and (b) on a planted region
holding TWO `json` fences, the FIRST is returned (the B1 ordering contract made
testable in isolation). No snapshot/property test warranted (same reasoning as
Work item 2).

Validation: same command quartet as Work item 2; all green. Commit referencing
roadmap 6.3.7.

### Work item 4 — Vacuous-pass hardening and planted-divergence proof (Stage C)

Implements: roadmap 6.3.7 success criterion's "fails if … diverges" — proven by
demonstrating red on a planted divergence; AGENTS.md "the new test … fails
before and passes after" and "ensure a snapshot/guard failure identifies a real
contract change".

Docs to read first: the deflation guard's vacuous-pass mitigations
(`_require_index`, slice-presence asserts). Skills: `python-router` →
`python-testing`; optionally `python-verification` to confirm no
generative/property adversary is warranted (it is not — fixed-document inputs).

Steps:

1. Audit every anchor lookup and region slice in the guard. Confirm each uses
   the loud-failure helpers (`slice_doc_region` with its `source` label,
   `extract_fenced_json`'s missing-fence assertion) so a renamed heading or
   removed fence fails rather than yielding an empty region that passes
   vacuously. Add an explicit `test_regions_are_non_empty` that asserts the
   SKILL exit-table region, the SKILL envelope region, AND the design §3.1
   skeleton each contain their expected marker (`| 0 |`, `"schema_version"`, and
   `"working_dir"` respectively), so a future heading rename or wrong-fence pull
   (B1) cannot silently neuter the guard.
2. Prove the guard is genuinely red on divergence, *without committing a broken
   SKILL.md*. Do this with a transient local edit during development:
   temporarily change SKILL.md's `schema_version` cell to `2`, run
   `uv run pytest -q tests/test_skill_contract_drift_guard.py`, observe
   `test_skill_envelope_schema_version_matches_constant` fail, then revert the
   edit. Likewise temporarily delete the `| 4 | … |` row and observe
   `test_skill_exit_codes_cover_exactly_the_enum` fail, then revert. Record both
   transcripts in `Artifacts and notes`. (These edits are never committed; they
   are the red-test evidence the execplans skill and AGENTS.md require.)
3. **B3 (resolved): no inventory or test-count update is needed.** The round-1
   plan's "update `_KNOWN_SKILL_MARKDOWN` if it references the new test module"
   step was dead: `_KNOWN_SKILL_MARKDOWN` in
   `tests/test_state_layout_reference.py` (lines 55-64) is a frozenset of
   markdown DOCUMENTS under `skill/novel-ralph/`, pinned against a glob of
   `skill/novel-ralph/**/*.md` (`test_discovery_covers_known_skill_files`, line
   351); a `tests/` module can never appear in it. This planning round also
   searched the whole `tests/` tree and confirmed there is NO collected-test-
   module-count assertion, NO `tests/`-directory inventory frozenset, and NO
   `pytest_collect*`/`pytest_collection*` hook that a new module would trip (the
   only `tests/` references are a directory-existence check in
   `tests/test_conftest_helpers.py` line 29 and a docstring note in
   `tests/test_per_chapter_loop_bdd.py`). Adding the new module therefore breaks
   no commit gate; the implementer adds nothing here. If, contrary to this check,
   a collection-count guard is somehow encountered, that is a Tolerance breach
   (unexpected pre-existing tripwire) — stop and escalate rather than editing it.
4. Final docs gate, since the guard is docs-adjacent and the work item may touch
   wording: run the full quartet.

Validation:

    make all
    make markdownlint
    make nixie

Expected: all green; the new module's tests pass against the live, reverted
`SKILL.md`. Commit referencing roadmap 6.3.7, then update `Progress`,
`Outcomes & retrospective`, and the Status header to reflect completion.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: the new `tests/test_skill_contract_drift_guard.py` passes against the
  live `SKILL.md`; it fails (demonstrated transiently) when the SKILL
  exit-code table loses/gains a code, when an envelope field is renamed,
  reordered, added, or dropped, and when the SKILL `schema_version` value
  diverges from `ENVELOPE_SCHEMA_VERSION`. The contract suite
  (`tests/test_contract_*`) and the existing skill-guard suite
  (`tests/test_skill_deflation_guard.py`) stay green.
- Lint/typecheck: `make lint` passes (Ruff, 100% docstring coverage, pyright/ty
  as configured). `make all` is green end to end.
- Markdown: `make markdownlint` and `make nixie` pass (no Mermaid added; run to
  confirm the gate, per AGENTS.md lines 169-172).
- No production source under `novel_ralph_skill/` changed (verify with
  `git diff --name-only`; expected paths are only under `tests/` and, at most, a
  whitespace-neutral `skill/novel-ralph/SKILL.md` clarification recorded in the
  Decision Log).

Quality method (how we check):

- Run `make all` before and after each work item; run the markdown quartet on
  the final item. Use `git diff --name-only` to confirm the change surface
  matches the Constraints.
- The acceptance behaviour a human can verify: "Run
  `uv run pytest -q tests/test_skill_contract_drift_guard.py` and expect all
  tests passing; temporarily change the `schema_version` cell in
  `skill/novel-ralph/SKILL.md` to `2`, re-run, and expect
  `test_skill_envelope_schema_version_matches_constant` to fail; revert."

## Idempotence and recovery

- All steps are re-runnable. The guard reads files; it writes only new test
  files. Re-running `make all` is safe.
- The Work item 4 red-test demonstration uses transient, never-committed edits
  to `SKILL.md`; if interrupted mid-edit, `git checkout -- skill/novel-ralph/SKILL.md`
  restores it. Confirm `git status` is clean of `SKILL.md` before committing.
- If the guard reveals a *real* pre-existing drift between `SKILL.md` and the
  live contract (a Tolerance breach), stop, do not "fix" it by editing the
  contract or the table, and escalate per the Tolerances section.

## Artifacts and notes

Captured during implementation (the `SKILL.md` edits were transient and
reverted; `git status` confirmed `SKILL.md` clean before each commit):

- Red, planted `schema_version: 2` (envelope cell changed from `1` to `2`):
  `test_skill_envelope_schema_version_matches_constant` failed with
  `assert 2 == 1`. Reverted.
- Red, deleted exit-code row (the `| 4 | … |` row removed):
  `test_skill_exit_codes_cover_exactly_the_enum` failed with
  `assert {0, 1, 2, 3} == {0, 1, 2, 3, 4}` (extra item `4` on the enum side).
  Reverted.
- Green against the reverted, live `SKILL.md`: `16 passed` for the guard
  module; `1332 passed, 1 skipped` for the full `make all`.
- Change surface (`git diff --name-only main`): `tests/_skill_contract_scanner.py`,
  `tests/test_skill_contract_drift_guard.py`, and
  `docs/execplans/roadmap-6-3-7.md`. No file under `novel_ralph_skill/` and no
  `skill/novel-ralph/SKILL.md` content change.

## Interfaces and dependencies

Libraries/modules to use and why:

- `pytest` with the shared `read_repo_text` fixture (`tests/conftest.py`) — the
  sanctioned in-process repo-text reader; no subprocess, matching the
  prose-guard discipline.
- `novel_ralph_skill.contract.exit_codes.ExitCode` — imported as pure data to
  derive the expected code set and per-code keywords, tying the SKILL table to
  the code source named by the roadmap.
- `novel_ralph_skill.contract.envelope.Envelope` (via `dataclasses.fields`) and
  `ENVELOPE_SCHEMA_VERSION` — imported to derive the expected field order and
  the schema-version value.
- `dataclasses` (stdlib) for field introspection; `json` (stdlib) for parsing
  the fenced envelope skeletons.
- The same `read_repo_text` fixture also reads
  `docs/adr-003-shared-interface-contract.md` and
  `docs/novel-ralph-harness-design.md` for the cross-document agreement checks
  (WI2 ADR/design tables; WI3 design §3.1 skeleton). No new dependency: it is the
  same in-process reader, just pointed at two more in-repo docs.

Symbols that must exist at the end of the milestone, in
`tests/test_skill_contract_drift_guard.py` (and, if extracted,
`tests/_skill_contract_scanner.py`):

    # tests/_skill_contract_scanner.py  (pure functions over markdown text)
    def parse_markdown_table(region: str) -> list[tuple[str, ...]]: ...
    def extract_exit_code_meanings(
        rows: list[tuple[str, ...]],
    ) -> dict[int, str]: ...  # B2: code (col 0) -> Meaning (col 1) only,
                             #     column-count tolerant
    def extract_fenced_json(region: str, fence_lang: str = "json") -> str: ...
    def slice_doc_region(
        text: str, start: str, end: str, *, source: str
    ) -> str: ...  # source-labelled loud-failure slicer for cross-document use

    # tests/test_skill_contract_drift_guard.py
    class TestSkillExitCodeTableDriftGuard: ...   # WI2
    class TestSkillEnvelopeSkeletonDriftGuard: ...  # WI3
    class TestSkillContractScanner: ...           # parser unit tests (WI2/WI3)
    class TestSkillContractGuardNonVacuous: ...   # WI4

No new external dependency is introduced. No public API in
`novel_ralph_skill/` changes.

## Revision note

Initial draft (2026-06-26). Decomposes roadmap 6.3.7 into four ordered,
independently committable work items: red skeleton (folded into WI2 to keep
every commit gate-green), exit-code-table guard, envelope-skeleton guard, and
vacuous-pass hardening with a planted-divergence red/green proof. Scoped cuprum
and other locked external libraries out explicitly with rationale (Decision
Log), since the task is an in-process docs drift-guard. Pinned the working_dir
example-value carve-out between SKILL.md and design §3.1 as a verified
divergence the guard must not false-fail on.

Round-2 revision (2026-06-26), resolving the three round-1 logisphere
blockers. (B1) The design-side fence is now explicitly anchored: WI3 slices the
design doc to the §3.1 region (`### 3.1` → `### 3.2`, heading 137 → 212) BEFORE
extracting the first ```json fence (line 146), excluding the five-field
`novel done` example at line 365; a positive `working_dir`-present assertion in
the fixture and in `test_skill_envelope_matches_design_field_order`, plus an
extended `test_regions_are_non_empty`, make a wrong-fence pull fail loudly. New
Risk and Decision-Log entries record this. (B2) The exit-row extractor is
redefined as `extract_exit_code_meanings(rows) -> dict[int, str]`, keying code
(column 0) to the Meaning cell (column 1) only and ignoring later columns, so
design §3.2's fourth "Example" column no longer shifts cells; cross-table
comparison is by per-code keyword presence, not exact string, because the
Meaning wording differs across the three tables (verified). New Risk and
Decision-Log entries record this; the Interfaces signature is updated. (B3) WI4
step 3 no longer touches `_KNOWN_SKILL_MARKDOWN` — traced and confirmed it
enumerates `skill/novel-ralph/**/*.md` documents and can never reference a
`tests/` module — and this round searched the suite and confirmed NO
test-collection-count guard, `tests/` inventory, or `pytest_collect*` hook
exists, so the new module breaks no commit gate; the step is rewritten as a
no-op with that evidence. Advisories also actioned: stale line numbers corrected
or replaced by heading anchors (A1), the §3.1/§3.2 exit-table slip fixed
throughout (A2), the envelope-region end anchor pinned to `### Invocation
discipline` line 155 (A3), and the WI1→WI2 fold reaffirmed (A4). A new
Decision-Log entry keeps both the code-coupling and the ADR/design
cross-document checks (Wafflecat calibration): the roadmap clause names the
ADR/design agreement, so it is not dropped, but B1/B2 keep the parser surface
small. A further Decision-Log entry introduces the source-labelled
`slice_doc_region` helper so cross-document slice failures name the correct
file instead of the deflation guard's hard-coded "SKILL.md".

## Addenda

Lightweight, no-plan corrections folded onto this completed task after the
review of step 6.3 settled. Each runs as a no-review lightweight pass.

- [x] **6.3.7.1 (from review:6.3.7; low).** Extend this task's drift-guard with
  one assertion that the design §3.1 and ADR-003 `schema_version` values match
  `ENVELOPE_SCHEMA_VERSION`. The guard pins `SKILL.md`'s `schema_version` to the
  code and pins the SKILL-vs-design field order, but the design §3.1 and ADR-003
  copies' own `schema_version` value is not asserted against the code constant,
  so a drift introduced in design §3.1 alone (e.g. `schema_version: 2`) would
  slip past every existing guard. Closing this completes the §6.3 "documented
  once without per-command drift" hypothesis for the `schema_version` datum
  across all copies. Scope: one assertion added to the existing drift-guard test.
  Implementation note: ADR-003 carries the `schema_version` field only in prose
  with no literal envelope value, so the single assertion pins the design §3.1
  numeral; there is no ADR-003 numeral to assert.
