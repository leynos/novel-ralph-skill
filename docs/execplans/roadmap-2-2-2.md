# Implement `init`, `set-cursor`, and `advance-phase`

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

This plan delivers the three state-mutator subcommands of `novel-state` that
the spine has so far left as stubs: `init`, `set-cursor`, and `advance-phase`
(roadmap task 2.2.2; design §4.1). They are the first commands that *write*
`state.toml` through the harness, so after this change an operator (and the
harness loop) can:

1. Bootstrap a project. `novel-state init` creates the `working/` directory and
   an initial, schema-coherent `state.toml` from a title, a slug, and a target
   word count, with `phase.current = "premise"`, `phase.completed = []`, an
   empty chapter manifest, and zeroed counts (design §4.1 `init` row;
   state-layout.md "Initialisation"). Running `novel-state check` against the
   freshly initialised tree exits `0` with `ok: true`.
2. Move the drafting cursor safely. `novel-state set-cursor` advances the
   `(current_chapter, current_scene, current_beat)` cursor and **refuses an
   incoherent cursor** — a chapter past the manifest, or a scene/beat set while
   the cursor names no chapter — with exit `3` (state or input error), leaving
   the prior `state.toml` byte-for-byte intact (design §4.1 `set-cursor` row,
   §3.2, §5.2 invariant 6).
3. March the phase enum forward. `novel-state advance-phase` moves
   `phase.current` to the **next** enum member and appends the just-left phase
   to `phase.completed`, and **refuses any skip or out-of-order completion**
   with exit `3`, never the benign exit `1` the loop continues on (design §4.1
   `advance-phase` row, §3.2 the third-case paragraph, §5.1 the phase enum).

The load-bearing, observable contract this plan pins is the **refusal exit
code**: a refused mutator request returns exit `3`, not the benign-negative exit
`1` (design §3.2, lines 199-205; ADR-003 §3.2 the third case). The roadmap's
success criterion is exactly this: "a behavioural scenario shows an out-of-order
`advance-phase` is refused with exit `3` and leaves the prior state intact."

This is the *write* half of the `novel-state` slice. The read-only `check`
validator (task 2.1.2) and the lossless `tomlkit` round-trip plus atomic write
plus `[pending_turn]` bracket helper (task 2.2.1) already exist and are reused
unchanged; `recount` (task 2.3.1) and `check`/`reconcile`'s disk-evidence work
(task 2.3.2) are *not* in scope here.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **`tomlkit` is the only sanctioned writer.** `set-cursor` and `advance-phase`
  read, mutate, and re-write `state.toml` through the existing
  `novel_ralph_skill.state.document` helpers (`load_document` /
  `document_to_state` / `write_document_atomically`), never `tomli_w`, a
  hand-built serialiser, or `tomllib`-plus-side-channel (ADR-002; design §5.3).
  `init`, which creates a *new* file, builds a `tomlkit` document and writes it
  through the same `write_document_atomically` helper. `tomllib` still backs
  the read-only `load_state`/`parse_state` decode, but the **mutators must not
  load through `load_state`/`_load_or_state_error`**: that path returns a plain
  `tomllib` mapping, not the live `tomlkit.TOMLDocument` the mutators edit in
  place (Decision Log D2; see Constraint "Mutator load path").
- **Mutator load path.** `set-cursor` and `advance-phase` load the document via
  `load_document` (tomlkit), not `load_state` (tomllib). They translate load
  and parse faults to the exit-`3` channel through a **new**
  `_load_document_or_state_error(path) -> TOMLDocument` sibling of the existing
  `_load_or_state_error`, reusing the existing `STATE_INPUT_ERRORS` tuple
  unchanged (which already subsumes every fault the document path raises — see
  the Verified Facts section and Decision Log D4). The mutators never call
  `_load_or_state_error` (it returns a `State`, not a `TOMLDocument`).
- **Typed-view derivation is also exit-`3`-routed.** The mutators derive the
  typed `State` read view by calling `document_to_state(document)` through a
  **second new** helper, `_state_view_or_state_error(document) -> State`, which
  wraps that call under the *same* `STATE_INPUT_ERRORS` tuple. This is
  load-bearing: `document_to_state` → `parse_state` reads every required key by
  subscription (raising `NonExistentKey`/`KeyError`/`TypeError`) and constructs
  each phase with `Phase(value)` (raising `ValueError` on a bad phase string),
  and `contract/runner.py:run` catches *only* `CycloptsError` and
  `StateInputError` — any other exception propagates uncaught and the process
  exits `1`, breaching the exit-`3` refusal contract. A `state.toml` that is
  syntactically valid TOML but structurally incomplete (a missing required
  table or key, or a bad phase string) passes `load_document` cleanly and only
  fails inside `document_to_state`; therefore that call **must** be wrapped at
  its call site, not merely covered by `STATE_INPUT_ERRORS` membership. The
  mutators *never* call bare `document_to_state` (design §3.2; Decision Log D4,
  D8; Verified Facts "runner.run catch arms"; resolves round-2 blocking point
  BR2-1).
- **Atomic write discipline, reused not re-invented.** Every write goes through
  `write_document_atomically` (temp file in the target directory followed by
  `Path.replace`, design §3.4; `docs/scripting-standards.md` "Reading / writing
  files and atomic updates"). Do not add a second atomic-write implementation
  in the command module.
- **Validate before persist.** `set-cursor` and `advance-phase` apply the §5.2
  validator (`validate_state`, task 2.1.2) to the *proposed* state and refuse
  to write when it would violate any invariant — the write discipline "the work
  the state describes is written to disk and verified before `state.toml` is
  updated" (design §3.4) and the §4.1 "refuses incoherent cursors" / "refuses
  skips and out-of-order completion" rows. A refusal performs **no write** at
  all: the prior `state.toml` is byte-for-byte unchanged.
- **Refusal is exit `3`, never exit `1`.** A refused mutator request (incoherent
  cursor, phase skip, out-of-order completion, missing/unparseable state) is
  the contract's exit `3` (state or input error), routed through the existing
  `StateInputError` channel (design §3.2 lines 199-205; ADR-003 §3.2; the
  `runner.run` `except StateInputError` arm). It is never the benign exit `1`.
- **The shared contract, reused not re-negotiated.** The commands return a
  `CommandOutcome` and are driven by the shared `run` wrapper; the entry point
  pre-parses `--human` with `parse_global_flags` and stamps the fixed
  `working_dir="working"` into the `RunContext`, exactly as `check` does today
  (ADR-003 §3.1, §3.2; `commands/stub.py:novel_state`,
  `commands/novel_state.py`). No new envelope field, no new exit code, no
  `--working-dir` flag.
- **No narrative judgement.** These mutators move state structurally and enforce
  only the mechanical §5.2 invariants (plus the named
  `chapter-planning → drafting` populated-manifest precondition, design §4.1
  line 266); they make no narrative judgement (ADR-001; design §1).
  `advance-phase` enforces enum order, not whether the phase's prose work is
  "good enough".
- **Package targets and gates.** All new code lives under `novel_ralph_skill/`
  and is in `$(PYTHON_TARGETS)`, so it carries 100% `interrogate` docstring
  coverage, passes Ruff lint and format, Pylint, and `ty`. No code file exceeds
  400 lines (AGENTS.md lines 24-27). `requires-python = ">=3.14"`
  (`pyproject.toml` line 6), so 3.14 features are available.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, docstrings,
  comments, and commit messages (AGENTS.md; `en-gb-oxendict`).
- **No shell-out, no new runtime dependency.** v1 commands invoke no external
  process for their core logic (design §4 line 241: "None invokes an external
  process … so cuprum is required only where a command shells out (none do in
  v1)"). These mutators touch only the filesystem via `pathlib`/`tempfile`
  (through the `document.py` helper); they do not import `cuprum`. The
  `[project].dependencies` set (`cyclopts`, `tomlkit`) is unchanged.

## Tolerances (exception triggers)

Stop and escalate when any of these is breached rather than working around it.

- **Scope.** If the change requires touching more than 9 files or ~700 net new
  lines, stop and re-scope. The expected file set is: the command module
  (`novel_ralph_skill/commands/novel_state.py`, extended; or a small sibling
  `novel_ralph_skill/commands/_state_mutators.py` if the module would breach
  the 400-line cap — see Risk "module size"), a new initial-state builder module
  (`novel_ralph_skill/state/initial.py`), the `state/__init__.py` re-export,
  the command test module (`tests/test_novel_state_mutators.py`), the
  behavioural `.feature` file (`tests/features/advance_phase_refusal.feature`)
  and its step module (`tests/steps/advance_phase_steps.py` plus the
  `tests/test_advance_phase_bdd.py` binder), and `docs/developers-guide.md` —
  about eight files.
- **Interface.** If delivering the mutators forces a change to the public
  signature of `parse_state`, `load_state`, `load_document`,
  `document_to_state`, `validate_state`, any `state/schema.py` dataclass,
  `CommandOutcome`, `RunContext`, `run`, or `parse_global_flags`, stop and
  escalate — those are the 2.1.x / 2.2.1 / 1.3.x contracts other tasks depend
  on. (Adding subcommands to the `novel-state` Cyclopts app via `@app.command`
  is *not* such a change; `build_app` stays zero-argument and its existing
  `check` subcommand is untouched. Adding the *new* module-private helpers
  `_load_document_or_state_error` and `_state_view_or_state_error` beside the
  existing `_load_or_state_error` is also not such a change — they add no
  public surface.)
- **Dependencies.** No new runtime dependency beyond `cyclopts`/`tomlkit`, and
  no new dev/test dependency: `pytest-bdd` (8.1.0), `hypothesis`, `syrupy`, and
  `pytest-timeout` are already in `[dependency-groups].dev` (`pyproject.toml`).
  If a new dependency seems required, stop and escalate.
- **`init` overwrite semantics.** If the design's `init` row and state-layout.md
  "Initialisation" cannot be reconciled on whether `init` may run when
  `working/state.toml` already exists, stop and present the options (refuse
  with exit `3` versus overwrite) with trade-offs rather than guessing. (This
  plan's Decision Log records the proposed reading: refuse, exit `3`; see Risk
  "init idempotence". Surface this to the human reviewer rather than treating
  it as settled — advisory A1, round 1.)
- **Refusal-code regression.** If any refusal path (incoherent cursor, phase
  skip, out-of-order completion, terminal advance,
  empty-manifest-into-drafting, missing/unparseable state) is observed to exit
  `1` instead of `3` even once, stop: that is the exact defect §3.2 exists to
  prevent. Do not weaken the test to accept `1`.
- **Iterations.** If the property, behavioural, or snapshot suite still fails
  after 3 focused attempts on one work item, stop and document the blocker in
  the Decision Log.
- **Ambiguity.** If `tomlkit` cannot express a clean append to
  `phase.completed` or a clean re-assignment of the cursor scalars without
  reflowing surrounding layout in a way that breaks `check`'s read-back, stop
  and escalate with the trade-offs (this is judged low-risk: `set-cursor` and
  `advance-phase` edit *values* and append to one array, the surgical-edit case
  task 2.2.1 verified is exact; the append-to-array sub-case is pinned by a
  round-trip assertion in work item 4 — Risk "append round-trip").

## Risks

- Risk: `init` runs against an existing `working/state.toml` and silently
  clobbers a real project. Severity: high. Likelihood: medium. Mitigation: the
  design's `init` row is "Create `working/` and an initial `state.toml`"; this
  plan reads that as *create*, so `init` refuses with exit `3` when
  `working/state.toml` already exists, rather than overwriting (Decision Log
  D1). The directory-creation is `mkdir(parents=True, exist_ok=True)` so a
  partially-present `working/` (e.g. only `manuscript/`) does not crash, but
  the *state file* is never overwritten. A test pins the refusal. If review
  prefers overwrite semantics, that is the Tolerance "`init` overwrite
  semantics" escalation.
- Risk: `init` builds a document that `parse_state`/`check` cannot read because
  a required table or key is missing. Severity: high. Likelihood: medium (the
  parser is a strict boundary — `state/parse.py` reads every required key by
  subscription with no defaults, so any omission raises `KeyError`/`TypeError`
  → exit `3` on the very first `check`). Mitigation: `build_initial_document`
  emits the **full** required table set enumerated field-by-field against
  `state/parse.py` in work item 2, and the work-item-2 unit test asserts
  `parse_state(build_initial_document(...))` **succeeds** *before* asserting
  any field value or calling `validate_state` (Decision Log D5; round-1
  blocking point B1).
- Risk: `advance-phase` past `done` (the terminal phase) has no "next" member.
  Severity: medium. Likelihood: high (it is a boundary every implementer hits).
  Mitigation: advancing from `done` is itself an out-of-order/illegal
  transition refused with exit `3` (there is no successor in `PHASE_ORDER`); a
  test pins it. `advance-phase` computes the successor as
  `PHASE_ORDER[index(current) + 1]` and treats an index at the end of the tuple
  as a refusal.
- Risk: `advance-phase` into `drafting` requires a populated chapter manifest
  (design §4.1 line 266: "Advancing into `drafting` requires the chapter
  manifest to be populated"). Severity: medium. Likelihood: medium. Mitigation:
  this is a named precondition the §5.2 validator does **not** own (validate.py
  has no empty-manifest-into-drafting check); `advance-phase` refuses the
  `chapter-planning → drafting` transition with exit `3` when `state.chapters`
  is empty, in the command body. A test pins both the refusal (empty manifest)
  and the success (populated manifest, exit `0`), the latter on the explicitly
  constructed tree named in Decision Log D6 / work item 4.
- Risk: the proposed-state construction re-serialises through the *lossy* typed
  `State` model rather than editing the live `tomlkit` document, discarding
  comments/layout. Severity: high. Likelihood: low. Mitigation: follow the task
  2.2.1 discipline exactly — mutate the live `TOMLDocument` in place (set the
  cursor scalars, append to the `phase.completed` array, set `phase.current`),
  and build the typed `State` *only* as a read view via `document_to_state` to
  feed `validate_state`. The document is the write source; `State` is the
  validation view. A round-trip/comment-preservation assertion guards this.
- Risk: append round-trip. `advance-phase` appends to `phase.completed`, which
  on
  a freshly-`init`-ed tree is an *empty* `completed = []` array. The 2.2.1
  empirical probe verified value edits, not specifically append-to-empty-array.
  Severity: low. Likelihood: low. Mitigation: work item 4 adds a
  round-trip/comment-preservation assertion for the *append-to-array* sub-case
  (advisory A5, round 1): after `document["phase"]["completed"].append(value)`
  and the cursor/current edits, `tomlkit.dumps` re-serialises the untouched
  tables byte-for-byte and only the touched array/scalar change.
- Risk: the command module breaches the 400-line cap once three mutator bodies
  plus `init`'s builder land. Severity: medium. Likelihood: medium. Mitigation:
  keep the initial-state construction in a separate `state/initial.py` module,
  and if `novel_state.py` still approaches the cap, extract the mutator bodies
  into a sibling `commands/_state_mutators.py` that `build_app` imports
  (AGENTS.md "clear file boundaries"). Decide by line count at implementation
  time, not upfront. The new `_load_document_or_state_error` helper is ~12
  lines and lands beside `_load_or_state_error`; if it tips the module past
  400, the same extraction applies.
- Risk: `set-cursor`/`advance-phase` should bracket their write in a
  `[pending_turn]` record, but these are *single-file* (`state.toml`-only)
  mutations. Severity: low. Likelihood: low. Mitigation: design §3.4 scopes the
  `[pending_turn]` bracket to a *multi-file* turn ("a turn that touches several
  files … is not atomic as a whole"). A `set-cursor`/`advance-phase` that
  writes only `state.toml` is already atomic via `write_document_atomically`,
  so it does **not** need the bracket. `init` writes one state file plus an
  empty `log.md`; the `log.md` write precedes and is independent of the state
  write, and a partial `init` (log present, state absent) is reconciled by
  re-running `init` (which still refuses only if `state.toml` exists), so no
  bracket is required. The plan records this scoping decision (Decision Log D3)
  so a reviewer does not read the absent bracket as a gap; the `pending_turn`
  helper remains available to the genuinely multi-file mutators (`recount`,
  `reconcile`).
- Risk: an `init` slug/title with characters that break the filesystem-safe
  contract. Severity: low. Likelihood: low. Mitigation: `init` stores the slug
  and title verbatim into `[novel]` exactly as supplied (the corpus and schema
  treat them as opaque strings); slug *validation* is not a §5.2 invariant and
  is out of scope. The plan does not invent a slug validator.

## Progress

- [x] Work item 1: add the failing command-contract tests for the three
  mutators (red), scaffolded against not-yet-registered subcommands.
  Done 2026-06-23: `tests/test_novel_state_mutators.py` drives `init`,
  `set-cursor`, and `advance-phase` through `run`; bodies are `xfail(strict)`
  until each command lands. A `populated_chapter_planning_tree` fixture was
  added to `tests/corpus_fixtures.py` to keep the into-`drafting` success test
  within the argument-count gate (bundling the three corpus constructors into
  one fixture, mirroring `compile_probe`). `make all` green (295 passed, 17
  xfailed); coderabbit `--agent` reported 0 findings.
- [x] Work item 2: implement `init` (the initial-state builder plus the `init`
  subcommand) green, with the full-table-set parse assertion.
  Done 2026-06-23: `novel_ralph_skill/state/initial.py` exposes
  `build_initial_document`, re-exported from `state/__init__.py`. The `init`
  subcommand (`novel_state.py` `_init` plus the `@app.command`) refuses an
  existing `state.toml` with exit `3`, creates the six-directory skeleton plus
  `log.md`, and writes through `write_document_atomically`. Unit tests in
  `tests/test_state_initial.py` assert `parse_state(...)` **succeeds** before any
  field assertion (B1), then the initial fields, then `validate_state` is empty.
  `datetime` is aliased `dt` (ruff ICN), and `validate_state(...) == ()` became
  `not validate_state(...)` (pylint C1803). `make all` green (302 passed, 14
  xfailed); coderabbit `--agent` reported 0 findings.
- [x] Work item 3: implement `set-cursor` (load via `load_document`;
  validate-before-persist; refuse with exit `3`) green, with the document-load
  fault-translation helper.
  Done 2026-06-23: the two helpers (`_load_document_or_state_error`,
  `_state_view_or_state_error`) plus the `set_cursor` body live in a new
  `novel_ralph_skill/commands/_state_mutators.py` (extracted per Risk "module
  size" so `novel_state.py` stays under 400 lines; the deviation from the plan's
  "helpers in novel_state.py" is recorded in the Decision Log). `set-cursor` is
  registered on `build_app`. Unit tests pin the fault-subclass facts and both
  helpers; a Hypothesis property pins the "accepts exactly the coherent cursors"
  equivalence to `validate_state`. `make all` green (315 passed, 8 xfailed);
  coderabbit `--agent` reported 0 findings.
- [x] Work item 4: implement `advance-phase` (next-member march; refuse skips,
  out-of-order, terminal, and empty-manifest-into-drafting with exit `3`)
  green, with the behavioural refusal scenario on the named corpus tree.
  Done 2026-06-23: the `advance_phase` body (in `_state_mutators.py`) refuses an
  already-incoherent prior (the only out-of-order refusal possible, D7), the
  terminal `done` (no successor in `PHASE_ORDER`), and `chapter-planning →
  drafting` with an empty manifest, then appends the left phase and sets the
  successor before validating and writing. The `pytest-bdd` scenario
  (`tests/features/advance_phase_refusal.feature` plus its step module and
  binder) proves the out-of-order refusal on `INCOHERENT_VARIANTS[
  "completed-prefix-gap"]`. An append-round-trip unit test pins that only the two
  touched `[phase]` keys change. All mutator xfails are gone. `make all` green
  (325 passed); coderabbit `--agent` reported 0 findings.
- [x] Work item 5: re-export any new public surface, snapshot the three
  envelopes, document the mutators in the developers' guide, and run the full
  gate.
  Done 2026-06-23: `build_initial_document` is re-exported and pinned in a
  public-surface test. `tests/test_novel_state_mutator_snapshots.py` snapshots
  the `init` success, `set-cursor` refusal, and `advance-phase` refusal
  envelopes (timestamp normalised), each paired with a semantic exit-code/`ok`
  assertion. A
  "State mutators" subsection was added to `docs/developers-guide.md` (the
  validate-before-persist discipline, the exit-`3` refusal, the two-helper load
  path, `init` create-not-overwrite, and the prior-state-only out-of-order
  refusal mechanism, AR2-1). The `novel_state.py` and `state/__init__.py`
  docstrings were refreshed. `make all`, `make markdownlint`, and `make nixie`
  all green (329 passed); coderabbit `--agent` reported 0 findings.

## Surprises & discoveries

- Observation: the exit-`3` `run` arm emits only `messages` (no `result`), so a
  refused mutator cannot name the breached invariant in `result.violations` the
  way `check`'s exit-`4` path does. Evidence: `contract/runner.py:run` builds the
  refusal `CommandOutcome` with only `messages=list(exc.messages)` and a default
  empty `result`; changing `run` is a Tolerance escalation. Impact: the refusal
  message names the breached invariant(s) first in `messages` (via
  `_refuse_if_incoherent`), and the work-item-1 `set-cursor` refusal test asserts
  `cursor-coherent` appears in `messages`, not `result`.
- Observation: `set-cursor` must derive the typed view (proving structural
  completeness) *before* mutating `document["drafting"]`. Evidence: editing
  `document["drafting"]` on a valid-but-incomplete document (e.g.
  `schema_version = 1`) raises `NonExistentKey` uncaught → exit `1`. Impact: the
  body calls `_state_view_or_state_error(document)` first (discarding the view),
  then mutates, then re-derives the proposed view for validation; this keeps the
  incomplete-document case on the exit-`3` channel (BR2-1).
- Observation: a fixture bundling the three corpus constructors
  (`populated_chapter_planning_tree`) was needed to keep both the into-`drafting`
  success test and the `set-cursor` Hypothesis property within the
  argument-count gate. Evidence: pylint R0913/R0917 fired at five parameters.
  Impact: the corpus construction lives in `tests/corpus_fixtures.py`, not inline.

## Decision log

- Decision (implementation deviation): the two document-load helpers and the
  `set-cursor`/`advance-phase` bodies live in a new
  `novel_ralph_skill/commands/_state_mutators.py`, not in `novel_state.py` as the
  plan's interface sketch suggested. Rationale: `novel_state.py` already held
  `check`, `init`, the shared constants, and `_load_or_state_error`; adding two
  more mutator bodies plus helpers would breach the 400-line cap (AGENTS.md). The
  plan's Risk "module size" explicitly sanctioned this extraction. The sibling
  imports `STATE_INPUT_ERRORS`/`WORKING_DIR_NAME` from `novel_state.py`, and
  `build_app` imports the sibling lazily (inside the builder) to avoid a circular
  import. No public surface changed. Date/Author: 2026-06-23, implementation
  agent.
- Decision: `init` refuses (exit `3`) when `working/state.toml` already exists
  rather than overwriting. Rationale: the design §4.1 `init` row says "Create …
  an initial `state.toml`" and state-layout.md "Initialisation" frames it as
  the first-turn bootstrap ("working/ does not exist"); silently clobbering a
  live project's state would violate the "State is precious. Never delete files
  in `working/`" hygiene rule (state-layout.md "Working directory hygiene").
  Refusal is the safe reading and is the Tolerance escalation point if review
  disagrees; surface it to the human reviewer as a decision, not a derivation
  (advisory A1). Date/Author: 2026-06-23, planning agent.
- Decision: the proposed-state for `set-cursor`/`advance-phase` is built by
  mutating the live `tomlkit` document, with `document_to_state` giving the
  typed read view for `validate_state`. Rationale: re-serialising from the lossy
  `State` would defeat ADR-002 (task 2.2.1 Decision Log). The document is the
  write source; `State` is the validation view. Date/Author: 2026-06-23,
  planning agent.
- Decision: `set-cursor`, `advance-phase`, and `init` write only `state.toml`
  (and
  `init` an empty `log.md`), single files, so they use
  `write_document_atomically` directly and do **not** open a `[pending_turn]`
  bracket. Rationale: design §3.4 scopes the bracket to a *multi-file* turn; a
  single `Path.replace` is already atomic. The bracket belongs to the
  multi-file mutators (`recount`, `reconcile`, tasks 2.3.x). Date/Author:
  2026-06-23, planning agent.
- Decision: the mutators load the document through a new
  `_load_document_or_state_error(path) -> TOMLDocument` helper that wraps
  `load_document(path)` (and, where the body needs the typed view,
  `document_to_state`) under the **existing** `STATE_INPUT_ERRORS` tuple,
  unchanged. Rationale: the existing `_load_or_state_error` returns a `State`
  from `tomllib`, not the `tomlkit.TOMLDocument` the mutators must edit in
  place (Decision D2). The existing `STATE_INPUT_ERRORS` tuple
  (`OSError, tomllib.TOMLDecodeError, KeyError, ValueError, TypeError`) already
  subsumes every fault the tomlkit document path raises: `tomlkit`'s
  `UnexpectedCharError`/`UnexpectedEofError`/`ParseError` are all `ValueError`
  subclasses, `NonExistentKey` (raised by `parse_state` over an incomplete
  document) is a `KeyError` subclass, `path.read_text` raises `OSError`, and a
  bad phase string raises `ValueError`. These subclass facts are pinned
  empirically in the Verified Facts section and re-pinned by a unit test in
  work item 3, so the tuple needs **no** extension; `tomllib.TOMLDecodeError`
  is simply inert on the document path. **Subsumption is necessary but not
  sufficient**: the tuple only catches a fault at a call site that *wraps* the
  raising call. The `load_document` call is wrapped by
  `_load_document_or_state_error`; the *separate* `document_to_state` call
  (which can raise on a valid-but-incomplete document) is wrapped by the new
  `_state_view_or_state_error` (Decision Log D8). Resolves round-1 blocking
  point B2; the call-site gap is closed by D8 (round-2 BR2-1). Date/Author:
  2026-06-23, planning agent.
- Decision: a **second** new helper,
  `_state_view_or_state_error(document) -> State`, wraps
  `document_to_state(document)` under the same `STATE_INPUT_ERRORS`
  tuple, and the mutators call it everywhere they previously called bare
  `document_to_state`. Rationale: `contract/runner.py:run` catches only
  `CycloptsError` and `StateInputError`; any other exception exits `1`, not the
  contract's `3`. A `state.toml` that is valid TOML but structurally incomplete
  (e.g. `schema_version = 1` alone) passes `load_document` and raises
  `NonExistentKey`/`KeyError`/`TypeError` only inside `document_to_state` →
  `parse_state`; a bad phase string raises `ValueError` from `Phase(...)`. Left
  unwrapped, these exit `1`, breaching the load-bearing exit-`3` refusal
  contract (design §3.2; Tolerance "Refusal-code regression"). Decision D4's
  subsumption claim is true but applies only at a wrapping call site, which bare
  `document_to_state` is not. A work-item-1 contract test drives `set-cursor`
  and `advance-phase` against `working/state.toml = "schema_version = 1\n"`
  asserting exit `3` (not `1`), and a work-item-3 unit test asserts
  `_state_view_or_state_error` over a structurally-incomplete document raises
  `StateInputError`. Resolves round-2 blocking point BR2-1. Date/Author:
  2026-06-23, planning agent.
- Decision: `build_initial_document` emits the full required table set
  field-by-field against `state/parse.py`, and the work-item-2 unit test asserts
  `parse_state(build_initial_document(...))` succeeds *before* asserting any
  field value or calling `validate_state`. Rationale: `state/parse.py` is a
  strict boundary (every required key read by subscription, no defaults), so an
  omitted key raises `KeyError`/`TypeError` → exit `3` on the first `check`.
  The full set, mirroring the corpus `_build_state_document`
  (`tests/working_corpus/_builder.py`), is enumerated in work item 2. Resolves
  round-1 blocking point B1. Date/Author: 2026-06-23, planning agent.
- Decision: `advance-phase` validates **both** the prior state (refuse exit `3`
  if it is already incoherent) and the proposed state (refuse exit `3` if the
  advance would leave it incoherent), in addition to the command-level terminal
  and empty-manifest preconditions. Rationale: `advance_phase()` takes no
  argument and always moves to the immediate successor, so it is *structurally
  incapable* of skipping a member. Against `validate.py`'s
  `_check_completed_prefix`, advancing a *coherent* prior state always yields
  another coherent state (the in-order prefix of the successor). The only
  out-of-order refusal therefore fires when the **prior** `completed` is
  already not the in-order prefix — i.e. the prior state is already incoherent.
  The design §3.2/§4.1 "refuses … out-of-order completion" is realised as: a
  prior state whose `completed` is out of order yields a proposed state that
  *still* fails `completed-prefix`, so the advance is refused. Validating the
  prior state explicitly first makes the refusal unambiguous and means the
  proposed-state validation can never launder an already-incoherent prior into
  a coherent successor. The BDD scenario (work item
  4) is built on the named corpus tree
     `INCOHERENT_VARIANTS["completed-prefix-gap"]`
  (a `drafting`-phase tree with `phase.completed = ("premise", "characters")`,
  which violates `completed-prefix`); advancing it keeps `completed-prefix`
  violated. Resolves round-1 blocking point B3. Date/Author: 2026-06-23,
  planning agent.
- Decision: the `advance-phase`-into-`drafting` success case is built from an
  explicitly constructed corpus tree — *not* a named `PHASE_STATES` fixture —
  via the `make_working_tree_spec` and `build_tree` fixtures
  (`tests/corpus_fixtures.py`) with `phase_current="chapter-planning"`,
  `phase_completed=PHASE_ORDER[:7]` (i.e. `premise` … `stc`), a non-empty
  `chapters=` of three `ChapterSpec` entries with `draft_words=0`,
  `has_done_flag=False`, `current_chapter=0`, `consecutive_clean=0`, and
  `convergence_target=1`. Rationale: `PHASE_STATES["chapter-planning"]` is a
  `_pre_drafting_spec` with an **empty** manifest
  (`tests/working_corpus/_library.py`), so
  `phase_state_tree("chapter-planning")` advances into the **empty-manifest
  refusal**, not the success path; no corpus fixture provides "chapter-planning
  with a populated manifest". Advancing the constructed tree (append
  `chapter-planning` to `completed`, set `current = "drafting"`) yields a state
  validated coherent: cursor at chapter `0` with a populated manifest is
  coherent (`0 <= current_chapter <= len(chapters)`), `by_chapter` sums to
  `0 == current` (invariant 3), and all knitting gates are false against the
  `0.0` ratio (invariant 7) — confirmed empirically in the Verified Facts
  section. Resolves round-1 blocking point B4. Date/Author: 2026-06-23,
  planning agent.
- Decision: `init` creates the full Initialisation directory skeleton —
  `working/{characters,world,reader,plan,manuscript,reviews}` — to match
  state-layout.md "Initialisation" step 1 verbatim, rather than deferring
  per-subdirectory creation. Rationale: the plan's Context and "Docs to read"
  sections claim fidelity to "state-layout.md Initialisation"; that source's
  step 1 is
  `mkdir -p working/{characters,world,reader,plan,manuscript,reviews}`, so
  silently omitting the skeleton would contradict the cited source of truth. No
  current invariant or `check` test depends on these directories, so creating
  them is inert with respect to validation, but it keeps `init` honest to its
  source and gives the later prose-writing phases their landing spots. Creation
  is idempotent (`mkdir(parents=True, exist_ok=True)` per subdirectory), so a
  partially-present `working/` does not crash. A work-item-2 test asserts the
  six subdirectories exist after `init`. Resolves round-2 blocking point BR2-2.
  Date/Author: 2026-06-23, planning agent.

## Outcomes & retrospective

Task closed 2026-06-23. All five work items landed as five atomic, gated
commits; `make all` is green at HEAD (329 passed) and `make markdownlint`/`make
nixie` pass for the Markdown changes. Each work item passed `coderabbit
--agent` with 0 findings.

Confirmed against the acceptance criteria:

- `init`/`set-cursor`/`advance-phase` each write through `tomlkit` plus the
  atomic `write_document_atomically`; `init` builds the full required table set
  and `check` accepts the freshly initialised tree.
- Every refusal path (incoherent cursor, out-of-order/terminal/empty-manifest
  advance, missing/unparseable/structurally-incomplete state) exits `3`, never
  `1`; the structurally-incomplete-but-valid-TOML case (BR2-1) is routed through
  `_state_view_or_state_error` and pinned by contract and unit tests.
- A refusal leaves `state.toml` byte-for-byte intact (asserted on every refusal
  test and the behavioural scenario).
- The behavioural out-of-order `advance-phase` scenario passes on the named
  `completed-prefix-gap` corpus tree.

Deviations from the plan (all recorded in the Decision Log / Surprises):

- The mutator bodies and the two load helpers live in a new
  `commands/_state_mutators.py`, not in `novel_state.py` (Risk "module size";
  the plan sanctioned this). `build_app` imports the sibling lazily to avoid the
  circular import the sibling's `STATE_INPUT_ERRORS`/`WORKING_DIR_NAME` import
  creates.
- Refusals name the breached invariant(s) in the envelope's `messages`, not
  `result.violations`: the exit-`3` `run` arm emits only `messages`, and
  changing `run` is a Tolerance escalation. The work-item-1 `set-cursor` refusal
  test asserts on `messages` accordingly.
- `set-cursor` derives the typed view *before* mutating `[drafting]` so a
  valid-but-incomplete document cannot make the scalar edit raise
  `NonExistentKey` uncaught (exit `1`).

Gaps the `recount`/`reconcile` tasks (2.3.x) must absorb: these single-file
mutators deliberately open no `[pending_turn]` bracket (Decision Log D3); the
multi-file mutators own that producer/consumer flow. The `advance-phase` detail
message reprs `Phase` members (e.g. `<Phase.PREMISE: 'premise'>`) because the
§5.2 validator's `completed-prefix` detail uses `{tuple(...)!r}`; if a later task
wants kebab strings in operator-facing detail, that is a `validate.py` change
outwith this task's scope.

## Context and orientation

The reader needs no prior plan. The relevant facts:

The harness's deterministic spine ships five console-scripts; `novel-state` is
the state command. Its read-only `check` subcommand and the four mutators
(`init`, `set-cursor`, `advance-phase`, `recount`, `reconcile`) all live behind
one Cyclopts app and the shared `run` wrapper (design §4.1, §3.1-§3.4). Today
only `check` is implemented; this task adds three of the mutators.

Files that already exist and that this task builds on (all DONE):

- `novel_ralph_skill/commands/novel_state.py` — the `novel-state` Cyclopts app.
  `build_app()` returns a zero-argument `cyclopts.App` configured with
  `result_action="return_value", exit_on_error=False, print_error=False, help_on_error=False`
  (so the shared `run` owns every exit and envelope) and registers one
  subcommand, `check`, via `@app.command`. It also exports
  `WORKING_DIR_NAME = "working"`, the helper
  `_load_or_state_error(path) -> State` (which maps `STATE_INPUT_ERRORS` to
  `StateInputError`, the exit-`3` channel, **via `load_state`/`tomllib` →
  returns a `State`**), and the `STATE_INPUT_ERRORS` tuple
  `(OSError, tomllib.TOMLDecodeError, KeyError, ValueError, TypeError)`. This
  task adds three more `@app.command` subcommands and a **new**
  `_load_document_or_state_error(path) -> TOMLDocument` sibling for the
  mutators' document load path; it does **not** reuse `_load_or_state_error` in
  the mutators (that returns a `State`, not a document).
- `novel_ralph_skill/state/document.py` — the lossless `tomlkit` writer:
  `load_document(path) -> TOMLDocument` (`tomlkit.parse(path.read_text(...))`),
  `document_to_state(document) -> State` (`parse_state` over the document),
  `write_document_atomically(document, path) -> None` (temp file in
  `path.parent` then `Path.replace`), and the `[pending_turn]` bracket
  (`open_pending_turn`/`clear_pending_turn`/`pending_turn`). All re-exported
  from `novel_ralph_skill/state/__init__.py`. The atomic-write helper is the
  one this task writes through; `load_document`/`document_to_state` are the
  mutators' load path.
- `novel_ralph_skill/state/parse.py` — `parse_state(mapping) -> State` (pure,
  structural) and `load_state(path) -> State` (`tomllib`-backed). Read-only; no
  §5.2 enforcement. **A strict boundary**: it reads every required table and
  key by subscription with no defaults (`raw["title"]`, `raw["created_at"]`,
  `raw["pass"]`, `raw["last_finding_counts"]{blocker,major,minor,taste}`,
  `raw["by_chapter"]`, …), so a document missing any required key raises
  `KeyError`/`TypeError`. This is exactly why `build_initial_document` must
  carry the full table set (work item 2 / B1).
- `novel_ralph_skill/state/schema.py` — the frozen typed `State` and its
  sub-shapes (`NovelMeta`, `PhaseState`, `ChapterEntry`, `Drafting`,
  `CriticState`, `FindingCounts`, `FangirlState`, `Gates`, `KnittingGates`,
  `FinalGate`, `WordCounts`, `PendingTurn`).
- `novel_ralph_skill/state/phase.py` — the closed eleven-member `Phase`
  `StrEnum` and `PHASE_ORDER = tuple(Phase)` in canonical order (`premise` …
  `done`). A member *is* its kebab-case string.
- `novel_ralph_skill/state/validate.py` —
  `validate_state(State) -> tuple[Violation, ...]` enforcing the §5.2
  *pure-state* invariants
  (`phase-in-enum`, `completed-prefix`, `by-chapter-sum`, the three convergence
  sub-rules, `cursor-coherent` inv 6 in its pure-state form,
  `gate-ratio-consistent`). An empty tuple means coherent. **It owns no
  empty-manifest-into-drafting check**; that precondition (design §4.1 line
  266) is the `advance-phase` command body's, enforced explicitly. This is the
  validator the mutators apply to the *proposed* state before writing.
- `novel_ralph_skill/contract/runner.py` —
  `CommandOutcome(code, result, messages)` (the value a body returns),
  `StateInputError` (raise to signal exit
  `3`), `RunContext`, `run(app, argv, context)` (drives the app, maps a
  `CycloptsError` to exit `2`, a `StateInputError` to exit `3`, and a body
  `CommandOutcome` to its `code`), and
  `parse_global_flags(argv) -> (human, residual)`.
- `novel_ralph_skill/contract/exit_codes.py` — the `ExitCode` enum:
  `SUCCESS=0`, `BENIGN_NEGATIVE=1`, `USAGE_ERROR=2`, `STATE_ERROR=3`,
  `ACTIONABLE_FINDING=4`. Mutator success is `SUCCESS`; refusal is
  `STATE_ERROR`.
- `novel_ralph_skill/commands/stub.py:novel_state()` — the real entry point:
  it pre-parses `--human` with `parse_global_flags(sys.argv[1:])`, then calls
  `run` with `build_app()`, the residual argv, and a `RunContext` stamping
  `command="novel-state"` and `working_dir=WORKING_DIR_NAME`. This task needs
  **no change** here; the new subcommands ride the same entry point.

Test scaffolding that already exists:

- `tests/conftest.py` — shared fixtures. It registers the corpus plugin via
  `pytest_plugins = ("corpus_fixtures",)`.
- `tests/corpus_fixtures.py` — the `working/` corpus as fixtures. The ones this
  task uses: `make_working_tree_spec` (returns the `WorkingTreeSpec`
  constructor), `make_chapter_spec` (the `ChapterSpec` constructor),
  `build_tree` (returns `build_working_tree`, callable `(spec, dest) -> Path`
  returning the `working/` directory), `phase_state_tree(phase) -> Path` (a
  factory building `PHASE_STATES[phase]`), `baseline_tree() -> Path`,
  `phase_names` (the `PHASE_ORDER` tuple), and
  `incoherent_tree(name) -> (spec, working_dir, expected_invariant)` (a factory
  building a named `INCOHERENT_VARIANTS` tree). **Note**: the constructors are
  `WorkingTreeSpec`/`ChapterSpec` and the builder is `build_working_tree`
  (round 1's review prose referred to these as `make_working_tree_spec`/
  `build_tree`, which are the *fixture names* that hand back those exact
  callables).
- `tests/test_novel_state_check.py` — the existing `check` contract tests, the
  template this task's mutator tests follow: a `_run_check` helper driving
  through `run` with a `RunContext`, a `_capture_envelope` helper reading the
  JSON envelope from `capsys`, tests driven through the real
  `stub.novel_state()` entry point under `monkeypatch.chdir(working.parent)`,
  and a POSIX-only installed-script e2e gated by
  `@pytest.mark.skipif(os.name != "posix")`, `@pytest.mark.slow`, and
  `@pytest.mark.timeout(180)`.
- `tests/features/torn_turn.feature` + `tests/steps/torn_turn_steps.py` +
  `tests/test_torn_turn_bdd.py` — the existing `pytest-bdd` pattern: a
  `.feature` file, a step module under `tests/steps/` (a package with
  `__init__.py`), and a binder module that
  `from steps.<module> import *  # noqa: F403` and calls
  `scenarios("features/<name>.feature")`.

Terms used in this plan:

- **Mutator.** A subcommand that writes `state.toml` (design §3.3 the
  command/query table). `init`, `set-cursor`, `advance-phase` are mutators;
  `check` is a checker (writes nothing).
- **Refusal / exit `3`.** A mutator asked to make a transition that conflicts
  with the current state (incoherent cursor, phase skip, out-of-order
  completion, missing/unparseable state) writes nothing and exits `3` (state or
  input error), never the benign exit `1` the loop continues on (design §3.2
  lines 199-205).
- **Proposed state.** The `state.toml` after a mutator's edit but before it is
  written; the mutator validates the *proposed* state (parsed via
  `document_to_state`) and writes only if it is coherent.
- **Cursor.** The `(current_chapter, current_scene, current_beat)` triple in
  `[drafting]` naming where drafting is (state-layout.md "Drafting sub-state";
  schema `Drafting`).

## Plan of work

Work proceeds in five atomic, independently committable, gate-passable work
items, each ending in validation. The order is test-first (red) then
per-command implementation (green), so each command lands with its own contract
proof.

Stage A (work item 1) is red scaffolding: the contract tests for all three
mutators, marked `xfail` until their subcommand lands, so the gate stays green
at commit. Stages B-D (work items 2-4) implement one command each, removing its
`xfail`s. Stage E (work item 5) is snapshots, export, docs, and the full gate.

### Work item 1 — Failing mutator-contract tests (red)

Add `tests/test_novel_state_mutators.py` driving the three not-yet-registered
subcommands through `run` (mirroring `tests/test_novel_state_check.py`'s
`_run_check` helper and
`RunContext(command="novel-state", working_dir="working", human=...)`, and its
`_capture_envelope`). Each test that exercises a subcommand body is marked
`xfail(strict=True, reason="…work item N")` until that command lands, so
`make all` is green at commit. Tests to add (failing now):

- `init` success: in an empty `tmp_path` (no `working/`),
  `novel-state init --title T --slug s --target-word-count 80000` exits `0`,
  creates `working/state.toml`, and the resulting tree passes
  `novel-state check` (exit `0`, `ok: true`); the state has
  `phase.current == "premise"`, `phase.completed == []`, empty `[chapters]`, and
  `[novel].target_word_count == 80000`.
- `init` refusal: when `working/state.toml` already exists (from
  `baseline_tree`,
  `monkeypatch.chdir(working.parent)`), `init` exits `3` and leaves the
  existing state byte-for-byte unchanged.
- `set-cursor` success: on a `drafting`-phase tree with a populated manifest
  (`phase_state_tree("drafting")`, three chapters), set the cursor to an
  explicitly pinned in-range value — `chapter=2, scene=0, beat=0` (a chapter
  index within `1..len(chapters)`, leaving scene/beat at their valid defaults
  so the test does not accidentally assert `chapter=0` with a non-zero
  scene/beat, which the validator refuses; AR2-2). This exits `0`, and a
  follow-up `check` exits `0`. Assert the written
  `[drafting].current_chapter == 2`.
- `set-cursor` refusal: setting `current_chapter` past the manifest length (or a
  scene/beat with `current_chapter == 0`) exits `3`, names the
  `cursor-coherent` invariant in `result`, and leaves `state.toml`
  byte-for-byte unchanged.
- `advance-phase` success (pre-drafting): from a coherent non-terminal phase
  whose successor is *not* `drafting` (e.g. `phase_state_tree("premise")`),
  advancing moves `phase.current` to the next member and appends the left phase
  to `phase.completed`; a follow-up `check` exits `0`.
- `advance-phase` success (into `drafting`): from the explicitly constructed
  populated-manifest `chapter-planning` tree (Decision Log D6 / Verified
  Facts), advancing into `drafting` exits `0` and a follow-up `check` exits `0`.
- `advance-phase` refusal (out-of-order): from the named corpus tree
  `incoherent_tree("completed-prefix-gap")` (a `drafting`-phase tree whose
  `phase.completed` is already not the in-order prefix), `advance-phase` exits
  `3` and leaves the prior state intact (this is the roadmap success criterion,
  also covered behaviourally in work item 4).
- `advance-phase` terminal refusal: advancing from `done`
  (`phase_state_tree("done")`) exits `3`.
- `advance-phase` empty-manifest refusal: advancing into `drafting` from
  `phase_state_tree("chapter-planning")` (empty manifest) exits `3`.
- Missing/unparseable state: `set-cursor` and `advance-phase` against a cwd with
  no `working/state.toml`, and against an unparseable one (e.g.
  `(working / "state.toml").write_text("not = toml =")`), each exit `3` (the new
  `_load_document_or_state_error` channel).
- **Structurally-incomplete-but-valid-TOML state (BR2-1)**: `set-cursor` and
  `advance-phase` against a `working/state.toml` that is *syntactically valid
  TOML but missing a required table* — written as
  `(working / "state.toml").write_text("schema_version = 1\n")` — each exit
  `3`, **not** `1`. This is the case `load_document` parses cleanly but
  `document_to_state` → `parse_state` rejects (`NonExistentKey`); it proves the
  typed-view derivation is routed through `_state_view_or_state_error`, closing
  the exit-3 channel gap. Assert the exit code is exactly
  `ExitCode.STATE_ERROR` (3); a test that accepts `1` is the Tolerance
  "Refusal-code regression" failure.

Docs to read first: design §4.1 (the `novel-state` subcommand table), §3.2
(exit codes and the third-case refusal paragraph), §5.2 (the invariants the
proposed state must satisfy), §5.1 (the phase enum and initial state);
`docs/adr-003-shared-interface-contract.md` §3.1-§3.2; AGENTS.md "Python
verification and testing"; developers-guide "Checker/mutator segregation" and
"Invariant validation".

Skills to load: `python-router` → `python-testing` (the `run`-driven and
entry-point-driven contract tests, `monkeypatch.chdir`, `capsys` envelope
capture, `xfail`); `leta` for navigating the existing command and contract
symbols.

Tests this item adds: the failing contract tests above (CLI error-path coverage
per design §9 "CLI error-path tests assert the exit-code contract at its
boundaries", and the success paths). No behavioural or snapshot test yet (those
arrive in items 4 and 5).

Validation: `make all` — the new mutator-body tests are `xfailed`; the gate is
green. Commit the red scaffold only when `check-fmt`, `lint`, `typecheck`, and
the rest of the suite are green.

### Work item 2 — Implement `init` (green)

Add `novel_ralph_skill/state/initial.py` exposing the builder:

```python
build_initial_document(
    *, title: str, slug: str, target_word_count: int, created_at: str
) -> tomlkit.TOMLDocument
```

It builds a fresh `state.toml` document carrying **the full required table
set** — derived field-by-field from `state/parse.py` (the strict boundary),
mirroring the corpus `_build_state_document`
(`tests/working_corpus/_builder.py`). The required shape, every key of which
`parse_state` reads by subscription with no default (so all must be present):

- `schema_version = 1` (top-level; `parse_state` reads `raw["schema_version"]`).
- `[novel]`: `title` (verbatim), `slug` (verbatim), `target_word_count`
  (= `target_word_count`), and **`created_at`** (the generated RFC 3339 UTC
  timestamp; `_novel` reads `raw["created_at"]`).
- `[phase]`: `current = "premise"`, `completed = []` (an empty array).
- `[drafting]`: `current_chapter = 0`, `current_scene = 0`, `current_beat = 0`,
  and the two required sub-tables:
  - `[drafting.critic]`: **`pass = 1`** (the on-disk key is the keyword `pass`,
    read at `parse.py` as `raw["pass"]`), `consecutive_clean = 0`,
    `convergence_target = 1` (the §5.1 default), and **`last_finding_counts`** as
    an inline table carrying **all four** of `blocker = 0`, `major = 0`,
    `minor = 0`, `taste = 0` (`_finding_counts` reads each).
  - `[drafting.fangirl]`: **`last_chapter_passed = 0`** (`_drafting` reads
    `_table(raw, "fangirl")["last_chapter_passed"]`).
- `[gates.knitting]`: **`done_30 = false`, `done_50 = false`, `done_80 = false`
  **
  (all three read by `_gates`).
- `[gates.final]`: **`final_pass_complete = false`**.
- `[word_counts]`: `target = target_word_count`, **`current = 0`**, and a
  **present (empty)** `by_chapter` inline table (`_word_counts` subscripts
  `raw["by_chapter"]`, so it must exist even when empty).
- `[[chapters]]`: an empty array (`parse_state` reads `raw["chapters"]`; the
  empty array yields an empty manifest tuple).
- **No** `[pending_turn]` table (the initial state has no in-flight turn;
  `parse_state` reads `raw.get("pending_turn")`, so its absence is fine).

Build the inline tables with `tomlkit.inline_table()` (mirroring `_inline` in
`tests/working_corpus/_builder.py`) and the nested tables with
`tomlkit.table()`. Do **not** import test code into the package — re-derive the
shape from `state/parse.py`.

Add the `init` subcommand to `build_app` via `@app.command`, with a Cyclopts
signature `init(*, title: str, slug: str, target_word_count: int = 80000)`
(keyword options; `target_word_count` defaults to the state-layout.md "default
80000"). The body: resolve `working = pathlib.Path(WORKING_DIR_NAME)`; if
`working / "state.toml"` exists, raise `StateInputError` (exit `3`, the
refusal); else `working.mkdir(parents=True, exist_ok=True)` **and create the
full Initialisation directory skeleton** — `working / name` for each `name` in
`("characters", "world", "reader", "plan", "manuscript", "reviews")`, each with
`mkdir(parents=True, exist_ok=True)` — to match state-layout.md
"Initialisation" step 1
(`mkdir -p working/{characters,world,reader,plan,manuscript,reviews}`) verbatim
(Decision Log; BR2-2). Then build the document with a generated `created_at`
(an RFC 3339 UTC timestamp via
`datetime.datetime.now(datetime.UTC).isoformat()` or equivalent),
`write_document_atomically(document, working / "state.toml")`, and return
`CommandOutcome(code=ExitCode.SUCCESS, …)`. Create an empty `working/log.md`
too (state-layout.md "Initialisation" step 3), through a plain
`Path.write_text` — `log.md` is not `state.toml`, so the direct-edit guard
(`state-layout.md` recipes) does not apply. The six subdirectory names are
sourced verbatim from state-layout.md step 1; the creation is idempotent, so a
partially-present `working/` does not crash.

Keep `created_at` out of the snapshot's stable surface and out of the unit
test's equality: tests assert `phase.current`/`completed`/manifest/target,
**explicitly excluding** the timestamp (advisory A2), and the work-item-5
snapshot normalises it (per AGENTS.md "Redact or normalize nondeterministic
fields such as timestamps").

Docs to read first: design §4.1 (the `init` row), §5.1 (the schema and the
three added fields — manifest, `convergence_target`, `[pending_turn]`);
state-layout.md "Initialisation" and "state.toml schema"; AGENTS.md
"Documentation maintenance"; `tests/working_corpus/_builder.py`
`_build_state_document` (the reference table shape, read for the field set only
— not imported).

Skills to load: `python-router` → `python-data-shapes` (building the `tomlkit`
document to the schema shape) and, if the timestamp typing needs it,
`python-types-and-apis`; `leta`.

Tests this item turns green: the two `init` tests (success and existing-state
refusal). Add a unit test that **first** asserts the parse succeeds:

```python
state = parse_state(
    build_initial_document(
        title="T",
        slug="s",
        target_word_count=80000,
        created_at="2026-06-23T00:00:00Z",
    )
)
```

succeeds (no `KeyError`/`TypeError`), and only then asserts
`state.phase.current == Phase.PREMISE`, `state.phase.completed == ()`,
`state.chapters == ()`, and `state.word_counts.target == 80000`; and finally
that `validate_state(state)` returns an empty tuple (the initial state is
coherent). The success-then-fields ordering is the B1 prevention — it catches a
missing table before any field assertion masks it. Add a directory-skeleton
test: after a successful `init`, each of `characters`, `world`, `reader`,
`plan`, `manuscript`, and `reviews` is a directory under `working/` and
`working / "log.md"` exists (BR2-2; state-layout.md "Initialisation" step 1 and
step 3).

Validation: `make all` green.

### Work item 3 — Implement `set-cursor` (green), with the document-load fault helper

Add the document-load fault-translation helper to
`novel_ralph_skill/commands/ novel_state.py` (or the extracted
`_state_mutators.py`):

```python
def _load_document_or_state_error(path: pathlib.Path) -> TOMLDocument:
    """Load ``path`` into a ``tomlkit`` document, mapping faults to exit 3.

    Wraps :func:`load_document` under the same ``STATE_INPUT_ERRORS`` tuple the
    read-only loader uses; ``tomlkit`` parse faults are ``ValueError`` subclasses
    and ``parse_state``'s ``NonExistentKey`` is a ``KeyError`` subclass, so the
    existing tuple subsumes the document path without extension.
    """
    try:
        return load_document(path)
    except STATE_INPUT_ERRORS as exc:
        msg = f"cannot load {path}: {exc}"
        raise StateInputError(msg) from exc


def _state_view_or_state_error(document: TOMLDocument) -> State:
    """Derive the typed ``State`` read view, mapping faults to exit 3.

    A document that parses as TOML may still be structurally incomplete (a
    missing required table or key, or a bad phase string). ``document_to_state``
    -> ``parse_state`` then raises ``NonExistentKey``/``KeyError``/``TypeError``,
    and ``Phase(...)`` raises ``ValueError``. ``contract/runner.py:run`` catches
    only ``CycloptsError`` and ``StateInputError``, so an unwrapped fault here
    would exit 1, not the contract's 3. Wrapping the call under the same
    ``STATE_INPUT_ERRORS`` tuple routes it to the exit-3 channel.
    """
    try:
        return document_to_state(document)
    except STATE_INPUT_ERRORS as exc:
        msg = f"state is structurally incomplete: {exc}"
        raise StateInputError(msg) from exc
```

Add a unit test pinning the fault-subclass facts so a future `tomlkit`/
`tomllib` bump cannot silently regress the exit-`3` contract: assert
`issubclass(tomlkit.exceptions.ParseError, ValueError)` and
`issubclass(tomlkit.exceptions.NonExistentKey, KeyError)`, and that
`_load_document_or_state_error` over a missing path and over an unparseable
file each raise `StateInputError`. Add a companion unit test for
`_state_view_or_state_error` (BR2-1): a `tomlkit` document parsed from
`"schema_version = 1\n"` (valid TOML, missing every other required table) makes
`_state_view_or_state_error(document)` raise `StateInputError` (it would raise
`NonExistentKey` if called bare), and a document with a bad phase string
(`[phase]\ncurrent = "nope"\n…`) likewise raises `StateInputError` (it would
raise `ValueError` from `Phase(...)` bare). This pins that the typed-view
derivation cannot escape the exit-3 channel.

Add the `set-cursor` subcommand to `build_app`: signature
`set_cursor(*, chapter: int, scene: int = 0, beat: int = 0)` (Cyclopts maps the
`set_cursor` function name to the `set-cursor` command name; verify the exact
kebab mapping at implementation time and pin it with a test). The body:

1. `path = pathlib.Path(WORKING_DIR_NAME) / "state.toml"`.
2. `document = _load_document_or_state_error(path)` (exit `3` on
   missing/unparseable).
3. Mutate the live document's `[drafting]` scalars:
   `document["drafting"] ["current_chapter"] = chapter`,
   `["current_scene"] = scene`,
   `["current_beat"] = beat`.
4. `proposed = _state_view_or_state_error(document)` (exit `3` on a
   structurally-incomplete-but-valid-TOML document — **never** bare
   `document_to_state`, which would exit `1`; BR2-1);
   `verdict = validate_state(proposed)`.
5. If `verdict` is non-empty, raise `StateInputError` naming the violated
   invariant(s) (exit `3`, **no write**). Else
   `write_document_atomically( document, path)` and return
   `CommandOutcome(code=ExitCode.SUCCESS, …)`.

The refusal is exit `3` (`StateInputError`), never exit `1` — this is the §3.2
third-case contract. Because the document is only written after validation
passes, a refusal leaves `state.toml` byte-for-byte unchanged.

Docs to read first: design §4.1 (`set-cursor` row), §5.2 (invariant 6 cursor
coherence — the pure-state form the validator owns), §3.2 (refusal exit `3`);
`validate.py` `_check_cursor_coherent`.

Skills to load: `python-router` → `python-errors-and-logging` (raising
`StateInputError` with a precise message; narrow `except` on the load), and
`python-data-shapes`; `leta`.

Tests this item turns green: the `set-cursor` success and refusal tests, the
fault-subclass unit test above, the `_state_view_or_state_error` unit test, the
`set-cursor`-against-`"schema_version = 1\n"` contract test asserting exit `3`
(not `1`; BR2-1), plus a test asserting the refusal path wrote nothing
(byte-for-byte compare of `state.toml` before/after, as
`test_check_writes_nothing` does for `check`). Add a `hypothesis` property
(expected, not optional — advisory A3): over generated `(chapter, scene, beat)`
triples against a fixed populated manifest, `set-cursor` exits `0` iff
`validate_state` of the proposed state is empty, and exits `3` otherwise — this
pins the "set-cursor accepts exactly the coherent cursors" equivalence to the
validator (per AGENTS.md "property tests … when a change introduces an
invariant over a range of inputs", and design §9 over the validator). Confirm
via `python-verification` that Hypothesis (not CrossHair/mutmut) is the right
adversary before loading it; downgrade only with a recorded reason in the
Decision Log.

Validation: `make all` green.

### Work item 4 — Implement `advance-phase` with the behavioural refusal scenario (green)

Add the `advance-phase` subcommand to `build_app`: signature `advance_phase()`
(no arguments — it always moves to the *next* member). The body:

1. `path = pathlib.Path(WORKING_DIR_NAME) / "state.toml"`;
   `document = _load_document_or_state_error(path)` (exit `3` on
   missing/unparseable); `prior = _state_view_or_state_error(document)` (exit
   `3` on a structurally-incomplete-but-valid-TOML document — **never** bare
   `document_to_state`, which would exit `1`; BR2-1).
2. **Refuse an already-incoherent prior state**:
   `if validate_state(prior): raise StateInputError(...)` (exit `3`, no write).
   This is the explicit guard that
   makes "out-of-order completion" a refusal — an advance never launders a
   broken prior into a coherent successor (Decision Log D7).
3. Compute the successor: `index = PHASE_ORDER.index(prior.phase.current)`; if
   `index + 1 >= len(PHASE_ORDER)` (current is `done`, the terminal), refuse
   with exit `3` ("no phase after `done`").
4. `successor = PHASE_ORDER[index + 1]`. If `successor is Phase.DRAFTING` and
   `prior.chapters` is empty, refuse with exit `3` (design §4.1 line 266 — the
   drafting precondition; the validator does not own this).
5. Mutate the live document: append the *current* phase's string value to
   `document["phase"]["completed"]` and set
   `document["phase"]["current"] = successor.value` (the `StrEnum` value is the
   on-disk kebab string).
6. `proposed = _state_view_or_state_error(document)` (BR2-1: the same exit-3
   wrap; in practice the re-derivation after an in-place edit of an
   already-valid document cannot newly fail, but routing it through the helper
   keeps the call site uniform and never bare); `validate_state(proposed)`. A
   non-empty verdict refuses with exit `3`, writing nothing (defence in depth:
   step 2 already rejects the only prior states that could fail here).
   Otherwise write atomically and return `SUCCESS`.

Why the out-of-order refusal works (the B3 reconciliation, also in Decision Log
D7): `advance_phase()` takes no argument, so it can only ever move to the
immediate successor — it is *structurally incapable* of skipping a member.
Against `validate.py`'s `_check_completed_prefix`, advancing a *coherent* prior
state always yields another coherent state (the in-order prefix of the
successor). The only out-of-order refusal therefore fires when the **prior**
`completed` is already not the in-order prefix — i.e. the prior is already
incoherent (step 2 rejects it, and step 6 confirms the proposed state still
fails `completed-prefix`). Design §3.2/§4.1's "refuses … out-of-order
completion" is realised exactly this way: a prior whose `completed` is out of
order yields a proposed state that still fails `completed-prefix`, so the
advance is refused.

Add a round-trip/comment-preservation assertion for the append sub-case (Risk
"append round-trip", advisory A5): on a coherent tree, after the
`completed.append(...)` and the `current`/cursor edits, assert
`tomlkit.dumps(document)` differs from the prior bytes only in the touched
array and scalar — the untouched tables (`[novel]`, `[gates]`, comments)
survive byte-for-byte.

Add the behavioural scenario (the roadmap success criterion) as `pytest-bdd`:
`tests/features/advance_phase_refusal.feature` with a scenario "an out-of-order
advance-phase is refused with exit 3 and leaves the prior state intact",
`tests/steps/advance_phase_steps.py` (a step module under the existing
`tests/steps/` package), and a binder `tests/test_advance_phase_bdd.py`
(`from steps.advance_phase_steps import *  # noqa: F403`;
`scenarios("features/advance_phase_refusal.feature")`), mirroring the
`torn_turn` wiring. The **named, buildable** starting tree is
`incoherent_tree("completed-prefix-gap")` — a `drafting`-phase tree whose
`phase.completed = ("premise", "characters")` already violates
`completed-prefix` (`tests/working_corpus/_variants.py`); Given that `working/`
tree (built into the step's `tmp_path` and `monkeypatch.chdir`-ed into), When
`advance-phase` runs, Then the exit code is `3` and `state.toml` is
byte-for-byte unchanged. The exact invariant the proposed state violates is
`completed-prefix` (its `completed` is not the in-order prefix of either
`drafting` or, after the append, `final-pass`).

The success-into-`drafting` test (in `tests/test_novel_state_mutators.py`, not
the BDD file) is built on the **explicitly constructed** populated-manifest
`chapter-planning` tree (Decision Log D6). The construction lives in a dedicated
`populated_chapter_planning_tree` fixture (in `tests/corpus_fixtures.py`,
mirroring `compile_probe`'s bundling) rather than inline in the test, so the
test stays within the project's argument-count gate (a single fixture parameter
instead of three corpus constructors). The fixture builds a `WorkingTreeSpec`
with `phase_current="chapter-planning"`, `phase_completed=PHASE_ORDER[:7]` (i.e.
`premise` … `stc`), three `ChapterSpec` entries (`number=1..3`,
`draft_words=0`, `has_done_flag=False`), `target_words=80000`,
`consecutive_clean=0`, `convergence_target=1`, `current_chapter=0`; it builds
the tree with `build_working_tree(spec, tmp_path)`. Advancing into `drafting`
exits `0`, and the
advanced state stays coherent (cursor at chapter 0 with a populated manifest is
coherent, `by_chapter` sums to `0 == current`, gates all false against the
`0.0` ratio — confirmed in the Verified Facts section).
`PHASE_STATES["chapter-planning"]` (i.e.
`phase_state_tree("chapter-planning")`) is **not** usable here — it has an
empty manifest and hits the empty-manifest refusal, which is the *separate*
refusal test.

Docs to read first: design §4.1 (`advance-phase` row, line 266 drafting
precondition), §5.1 (phase enum and `advance-phase` "refuses any transition
that skips a member or completes phases out of order"), §3.2 (refusal exit
`3`); §9 ("behavioural tests … an out-of-order `advance-phase` is refused");
`phase.py` `PHASE_ORDER`; `validate.py` `_check_completed_prefix`;
`tests/working_corpus/_variants.py` (the `completed-prefix-gap` variant);
`tests/working_corpus/_library.py` (why `PHASE_STATES["chapter-planning"]` is
empty-manifest).

Skills to load: `python-router` → `python-errors-and-logging` and
`python-iterators-and-generators` (the successor computation); `python-testing`
for the `pytest-bdd` scenario/step/feature wiring; `leta`.

Tests this item turns green: the `advance-phase` pre-drafting success, the
into-`drafting` success (constructed tree), the out-of-order refusal
(`completed-prefix-gap`), the terminal refusal (`done`), and the
empty-manifest-into-drafting refusal (`phase_state_tree("chapter-planning")`)
tests, plus the behavioural scenario, plus the
`advance-phase`-against-`"schema_version = 1\n"` contract test asserting exit
`3` (not `1`; BR2-1). Assert each refusal exits `3` (never `1`) and writes
nothing.

Validation: `make all` green.

### Work item 5 — Snapshots, export, docs, and the full gate

Add snapshot coverage of the three mutators' machine-mode JSON envelopes
(`syrupy`, per design §9 "Snapshot tests pin the machine-mode JSON envelope per
command"), normalising the `created_at` timestamp and any absolute path so the
snapshot identifies a real contract change, not churn (AGENTS.md "Redact or
normalize nondeterministic fields"). Pair each snapshot with a semantic
assertion (the success/refusal exit code and the `result` keys) rather than
relying on the snapshot alone (AGENTS.md "pair them with semantic assertions").

If `build_initial_document` (or an extracted `commands/_state_mutators.py`)
adds public names, re-export them from `state/__init__.py` / the command
package as appropriate and update `__all__`. Update the `novel_state.py` and
`state/__init__.py` module docstrings that currently say the CLI/mutators are
"task 2.2.2" pending.

Add a "State mutators (`init`, `set-cursor`, `advance-phase`)" subsection to
`docs/developers-guide.md` under "State and on-disk layout", describing: the
validate-before-persist discipline, the exit-`3` refusal contract, the
**document load path** (mutators use `_load_document_or_state_error` →
`load_document`, not `_load_or_state_error` → `load_state`), the single-file (no
`[pending_turn]`) write, the `init` create-not-overwrite semantics, and the
`advance-phase` out-of-order refusal mechanism (prior-state coherence guard),
so the `recount`/`reconcile` tasks find the pattern. State plainly (AR2-1) that
because `advance-phase` takes no argument and always moves to the immediate
successor, a phase *skip* cannot be requested; "refuses out-of-order
completion" is therefore realised **solely** as the prior-state coherence guard
(a prior whose `completed` is not the in-order prefix is refused), so a future
reader does not hunt for skip-rejection logic that cannot exist. Also document
the two-helper load path: `_load_document_or_state_error` (load faults) and
`_state_view_or_state_error` (typed-view faults from a valid-but-incomplete
document), both routing to exit `3`, so neither escapes the channel (BR2-1).

Confirm the state-layout direct-edit guard
(`tests/test_state_layout_reference.py`) still passes unchanged: this task adds
sanctioned `novel-state` mutators, so the reference prose gains no hand-edit
*recipe* (the guard forbids direct `state.toml` writes outside `novel-state`;
these commands *are* `novel-state`).

Docs to read first: developers-guide "State and on-disk layout", "The
`document.py` round-trip writer", and "The state-layout direct-edit guard";
AGENTS.md "Markdown guidance" and "Documentation maintenance";
`docs/documentation-style-guide.md`.

Skills to load: `en-gb-oxendict` for the prose; `python-router` →
`python-testing` for the snapshot wiring.

Tests this item adds: the three envelope snapshots with paired semantic
assertions; an import-surface assertion if a new public name is re-exported.

Validation: `make all`; and because Markdown changed, `make markdownlint` and
`make nixie` (no Mermaid added, but run `nixie` per the standing rule for
Markdown changes). Paragraphs wrapped at 80 columns, code blocks at 120.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-2-2`.

1. Confirm the branch and a clean tree:

   ```bash
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-2-2 \
     branch --show-current
   # expect: roadmap-2-2-2
   ```

2. Work item 1: add `tests/test_novel_state_mutators.py` (red, `xfail`ed
   bodies):

   ```bash
   make all
   ```

   Expect the suite green with the mutator-body tests reported `xfailed`.

3. Work item 2: add `state/initial.py` and the `init` subcommand; remove the
   `init` `xfail`s:

   ```bash
   make all
   ```

   Expect the `init` success/refusal tests and the parse-succeeds-then-fields
   initial-state unit test passing.

4. Work item 3: add `_load_document_or_state_error`, implement `set-cursor`;
   remove its `xfail`s:

   ```bash
   make all
   ```

   Expect the `set-cursor` success/refusal/writes-nothing tests, the
   fault-subclass unit test, and the Hypothesis property passing.

5. Work item 4: implement `advance-phase` and add the behavioural scenario;
   remove its `xfail`s:

   ```bash
   make all
   ```

   Expect the `advance-phase` two success and three refusal tests plus the
   out-of-order behavioural scenario passing.

6. Work item 5: snapshots, export, docs. Because Markdown changed:

   ```bash
   make all
   make markdownlint
   make nixie
   ```

   Expect all three green. On the first snapshot run, generate with
   `make test PYTEST_ADDOPTS=--snapshot-update` (or the project's syrupy update
   invocation), review the `.ambr` diff, then re-run `make all` clean.

Commit after each work item with a clear, imperative, en-GB message (e.g. "Add
novel-state init mutator and initial-state builder"). Commit only when the gate
is green (AGENTS.md "Committing"). Use the `commit-message` skill.

## Validation and acceptance

Acceptance is behaviour a human can verify:

- **`init` bootstraps a coherent project.** In an empty directory,
  `novel-state init --title T --slug s --target-word-count 80000` exits `0`,
  creates `working/state.toml` with `phase.current = "premise"`,
  `phase.completed = []`, an empty `[chapters]` manifest, and
  `[word_counts].target = 80000`; a follow-up `novel-state check` exits `0` with
  `ok: true`. Re-running `init` where `working/state.toml` already exists exits
  `3` and leaves the existing state byte-for-byte unchanged (design §4.1;
  state-layout.md "Initialisation").
- **`set-cursor` refuses an incoherent cursor with exit `3`.** Setting a cursor
  within the manifest exits `0`; setting `current_chapter` past the manifest,
  or a scene/beat with no chapter, exits `3`, names `cursor-coherent` in
  `result`, and leaves `state.toml` byte-for-byte unchanged (design §4.1, §5.2
  inv 6, §3.2).
- **`advance-phase` marches forward and refuses skips with exit `3`.** Advancing
  a coherent non-terminal phase moves `phase.current` to the next member and
  appends the left phase to `phase.completed` (follow-up `check` exits `0`),
  including the populated-manifest `chapter-planning → drafting` success; an
  out-of-order advance (the `completed-prefix-gap` tree), an advance from
  `done`, and an advance into `drafting` with an empty manifest each exit `3`
  and write nothing. The out-of-order refusal is also proven by a `pytest-bdd`
  scenario (the roadmap success criterion; design §9, §3.2).
- **Missing/unparseable/incomplete state exits `3`.** `set-cursor`/
  `advance-phase`
  against a cwd with no `working/state.toml`, against an unparseable one, **and
  against a valid-TOML-but-structurally-incomplete one** (e.g.
  `working/state.toml = "schema_version = 1\n"`) each exit `3` — the first two
  through `_load_document_or_state_error`, the third through
  `_state_view_or_state_error` — never exit `1` (BR2-1). Pinned by contract
  tests driving both subcommands against the incomplete file, by the
  `_state_view_or_state_error` unit test, and by the fault-subclass unit test
  (so a `tomlkit`/`tomllib` bump cannot regress it).
- **No refusal exits `1`.** Every refusal path exits `3`, never the benign `1`
  (the §3.2 load-bearing distinction).

Quality criteria ("done" means):

- Tests: `make test` passes (`pytest -v -n $(PYTEST_XDIST_WORKERS)`), including
  the new contract, behavioural, snapshot, unit, and property tests.
- Lint/format/type: `make check-fmt`, `make lint` (Ruff + 100% `interrogate`
  docstring coverage + Pylint), and `make typecheck` (`ty`) all pass.
- Audit: `make audit` (`pip-audit`) passes; no new dependency.
- Markdown: `make markdownlint` and `make nixie` pass for the developers-guide
  and execplan edits.
- Aggregate: `make all` is green.

Quality method: run `make all` (and `make markdownlint`/`make nixie` for the
Markdown changes) locally before each commit; CI runs the same gates.

## Idempotence and recovery

Every step is re-runnable. `make all` is idempotent. The atomic write is
idempotent by construction (re-running a no-op write produces the same bytes).
`init` is *not* idempotent on a populated tree by design — it refuses rather
than overwrites (Decision Log D1); re-running it is safe (it changes nothing
and exits `3`). `set-cursor`/`advance-phase` are pure functions of the prior
state plus the argument, so re-running with the same input either re-writes
identical bytes (success) or refuses (exit `3`) without mutating. Tests mutate
only `tmp_path`. There is no destructive operation; recovery from a botched
edit is `git restore` of the in-progress change.

## Artifacts and notes

### Verified facts the plan relies on

Each checked against the worktree or the locked sources, not memory. The
library behaviours were confirmed empirically with `uv run python` against the
locked versions in this worktree (round 2).

- **Cyclopts 4.18.0** (`uv.lock`). Subcommands are registered with
  `@app.command`
  on the app `build_app` returns; the existing `check` subcommand proves the
  pattern (`commands/novel_state.py`). The app is configured
  `result_action="return_value", exit_on_error=False, print_error=False, help_on_error=False`
  so the shared `run` owns exits — the new subcommands inherit this. `--help`/
  `--version` are handled by Cyclopts and yield a non-`CommandOutcome` return
  that `run` treats as exit `0` with no envelope (`runner.run`). Cyclopts maps
  a function name to a command name by replacing underscores with hyphens
  (verified against the round-1 review's citation of the official "Commands"
  docs), so `set_cursor` becomes `set-cursor` and `advance_phase` becomes
  `advance-phase` automatically; the exact mapping is nonetheless pinned by a
  command-name test rather than asserted from memory.
- **`tomlkit` 0.15.0** (`uv.lock`). The round-trip helper (`state/document.py`,
  task 2.2.1) is the only writer; task 2.2.1's empirical probe confirmed a
  no-op round-trip is byte-identical and a surgical *value* edit rewrites only
  the touched bytes at 0.15.0. `set-cursor` (scalar edits) and `advance-phase`
  (scalar edit plus one array append) are value-level surgical edits, the case
  2.2.1 verified exact; the append-to-array sub-case gains its own round-trip
  assertion (work item 4). `init` writes a fresh document, no round-trip
  concern.
- **`tomlkit` fault hierarchy (B2 pin).** Verified in this worktree against
  tomlkit 0.15.0: `tomlkit.exceptions.ParseError.__mro__` is
  `[ParseError, ValueError, TOMLKitError, Exception, …]` — a **`ValueError`
  subclass**; the concrete parse faults `UnexpectedCharError` and
  `UnexpectedEofError` are `ParseError` subclasses (hence `ValueError`s) and
  are what `tomlkit.parse` raises on malformed input (e.g. `"key = "`,
  `"[unclosed"`, `"a = b c"`). `tomlkit.exceptions.NonExistentKey.__mro__` is
  `[NonExistentKey, KeyError, LookupError, TOMLKitError, …]` — a **`KeyError`
  subclass**; `document_to_state`/`parse_state` over an incomplete document
  raises `NonExistentKey`. A bad phase string raises a plain `ValueError`, and
  `path.read_text` raises `OSError`. Therefore the **existing**
  `STATE_INPUT_ERRORS` tuple (`OSError`, `tomllib.TOMLDecodeError`, `KeyError`,
  `ValueError`, `TypeError`)
  already subsumes every fault the document load path raises; the new
  `_load_document_or_state_error` reuses it unchanged, and
  `tomllib.TOMLDecodeError` is simply inert there. A unit test re-pins the two
  `issubclass` facts so a future bump cannot silently regress the exit-`3`
  contract.
- **`runner.run` catch arms (BR2-1 pin).** Verified by reading
  `novel_ralph_skill/contract/runner.py:run` in this worktree: the body has
  exactly two `except` arms — `except CycloptsError` (mapped to exit `2`) and
  `except StateInputError` (mapped to exit `3`). There is **no** broad
  `except Exception`; any other exception propagates uncaught and the
  interpreter exits `1`. Therefore a fault raised by `document_to_state`/
  `parse_state`/ `Phase(...)` over a valid-but-incomplete `state.toml` exits
  `1` unless wrapped at its call site in `StateInputError`. This is why the
  typed-view derivation must go through `_state_view_or_state_error` (Decision
  Log D8); subsumption by `STATE_INPUT_ERRORS` alone is insufficient without a
  wrapping call site. Confirmed: a valid-but-incomplete document such as
  `"schema_version = 1\n"` parses under `load_document` but raises
  `NonExistentKey` inside `parse_state` (`raw["title"]` and the other required
  keys are absent), and `Phase("nope")` raises `ValueError`.
- **`build_initial_document` required table set (B1 pin).** Verified
  field-by-field against `state/parse.py`: `parse_state` reads
  `raw["schema_version"]`; `[novel]` `title`/`slug`/`target_word_count`/
  `created_at`; `[phase]` `current`/`completed`; `[drafting]` `current_chapter`/
  `current_scene`/`current_beat`, `[drafting.critic]` `pass`/`consecutive_clean`
  /`convergence_target`/`last_finding_counts` (`{blocker,major,minor,taste}`),
  `[drafting.fangirl].last_chapter_passed`; `[gates.knitting]` `done_30`/
  `done_50`/`done_80`, `[gates.final].final_pass_complete`; `[word_counts]`
  `target`/`current`/`by_chapter`; and `raw["chapters"]`. Every one is read by
  subscription with no default, so all must be present. This is the exact set
  the corpus `_build_state_document` emits
  (`tests/working_corpus/ _builder.py`), confirming the shape.
- **`advance-phase` into `drafting` success tree (B4 pin).** Verified
  empirically
  in this worktree: a `WorkingTreeSpec` with `phase_current="chapter-planning"`,
  `phase_completed=PHASE_ORDER[:7]`, three `ChapterSpec` entries with
  `draft_words=0`/`has_done_flag=False`, `current_chapter=0`,
  `consecutive_clean=0`, `convergence_target=1`, built with
  `build_working_tree`, is coherent (`validate_state` empty); appending
  `chapter-planning` to `completed` and setting `current="drafting"` yields a
  state that is **also** coherent (`validate_state` empty) with three manifest
  chapters. So this is the buildable populated-manifest success case.
  `PHASE_STATES["chapter-planning"]` is a `_pre_drafting_spec` with an
  **empty** manifest (`tests/working_corpus/_library.py`), so
  `phase_state_tree("chapter-planning")` hits the empty-manifest refusal, *not*
  the success path — it is the separate refusal fixture.
- **`advance-phase` out-of-order refusal tree (B3 pin).** Verified empirically:
  `INCOHERENT_VARIANTS["completed-prefix-gap"]`
  (`tests/working_corpus/_variants.py`) is a `drafting`-phase tree with
  `phase.completed = ("premise", "characters")`; its prior `validate_state`
  reports `["completed-prefix"]` (already incoherent). Appending the current
  phase and setting `current="final-pass"` yields a proposed state whose
  `validate_state` *still* reports `["completed-prefix"]`. So the advance is
  refused (exit `3`) and the BDD scenario is built on this named, buildable
  corpus tree. The validator's `_check_completed_prefix` never refuses a
  *coherent* prior advancing to its immediate successor (the in-order prefix is
  preserved), so the refusal can only guard against an already-incoherent prior
  — which is exactly what the explicit prior-state guard (work item 4 step 2)
  makes unambiguous.
- **`cuprum` 0.1.0** (`uv.lock`; source `/data/leynos/Projects/cuprum`). These
  mutators shell out to nothing, so they do **not** import cuprum — confirmed
  against design §4 line 241 ("None invokes an external process for its core
  logic, so cuprum is required only where a command shells out (none do in
  v1)"). cuprum is used only by the POSIX-only installed-script *e2e* test, via
  the existing `single_program_catalogue` fixture: `cuprum.ProgramCatalogue`
  with a `ProjectSettings(programs=(Program(absolute_path),))` allowlists an
  absolute-path program, and
  `sh.make(prog, catalogue=…)(args).run_sync(context= ExecutionContext(cwd=…), capture=True)`
  runs it. The conftest fixture's own docstring records the API contract
  ("cuprum 0.1.0 allowlists any `Program` string, including an absolute path;
  the catalogue allowlist, not the `Program` type, is the execution gate"),
  verified against `cuprum/catalogue.py` `ProgramCatalogue` / `ProgramEntry`
  and the existing `test_novel_state_check.py` e2e. This plan adds **no** new
  cuprum usage; an installed-script e2e for the mutators is *optional* (the
  `check` e2e already proves the build-and-install path; design §9 and ADR-006
  keep e2e POSIX-only and `@slow`).
- **`pytest-bdd` 8.1.0**, **`hypothesis`**, **`syrupy`**, **`pytest-timeout`**
  are already in `[dependency-groups].dev` (`pyproject.toml`); the `torn_turn`
  feature/step/binder trio is the working template for the new behavioural
  scenario. No new dev dependency.
- **Initial-state shape** (state-layout.md "Initialisation"; design §5.1): first
  turn `working/` does not exist; create it with `phase.current = "premise"`,
  `phase.completed = []`, `target_word_count` from input or default `80000`,
  provisional `title`/`slug`, an empty `log.md`. The §5.1 additions
  (`convergence_target` default `1`, empty `[chapters]`, no `[pending_turn]`)
  complete the coherent initial document; `validate_state` of it is empty
  (verified via the work-item-2 unit test).

## Interfaces and dependencies

Use the locked `cyclopts` (4.18.0) and `tomlkit` (0.15.0), plus `pathlib`,
`datetime`, and `tempfile` from the standard library (the last via the existing
`document.py` helper). No new runtime dependency, no `cuprum`/`cmd-mox` import
in the command bodies.

In `novel_ralph_skill/state/initial.py`, define:

```python
# novel_ralph_skill/state/initial.py
from __future__ import annotations

import tomlkit
from tomlkit import TOMLDocument


def build_initial_document(
    *, title: str, slug: str, target_word_count: int, created_at: str
) -> TOMLDocument:
    """Build a fresh, schema-coherent ``state.toml`` document for ``init``.

    Carries every required §5.1 table the strict ``parse_state`` boundary reads
    by subscription: ``schema_version``, ``[novel]`` (with ``created_at``),
    ``[phase]`` (``current = "premise"``, ``completed = []``), ``[drafting]`` with
    its ``[drafting.critic]`` (``pass``, ``consecutive_clean``,
    ``convergence_target = 1``, ``last_finding_counts`` inline with
    ``blocker``/``major``/``minor``/``taste``) and ``[drafting.fangirl]``
    (``last_chapter_passed``) sub-tables, ``[gates.knitting]`` and
    ``[gates.final]`` all-false, ``[word_counts]`` (``target``, ``current = 0``,
    a present empty ``by_chapter`` inline table), and an empty ``[[chapters]]``
    array. ``parse_state(build_initial_document(...))`` succeeds and
    ``validate_state`` of the result is an empty tuple.
    """
```

In `novel_ralph_skill/commands/novel_state.py` (or an extracted
`commands/_state_mutators.py` imported by `build_app`), add the document-load
fault helper and register three new subcommands on the app `build_app` returns,
each returning a `CommandOutcome` and raising `StateInputError` to refuse:

```python
def _load_document_or_state_error(path: pathlib.Path) -> TOMLDocument:
    """Load ``path`` into a ``tomlkit`` document, mapping faults to exit 3."""


def _state_view_or_state_error(document: TOMLDocument) -> State:
    """Derive the typed ``State`` view from a document, mapping faults to exit 3."""


@app.command
def init(*, title: str, slug: str, target_word_count: int = 80000) -> CommandOutcome:
    """Create ``working/`` and an initial ``state.toml`` (design §4.1)."""


@app.command
def set_cursor(*, chapter: int, scene: int = 0, beat: int = 0) -> CommandOutcome:
    """Set the drafting cursor; refuse an incoherent cursor with exit 3."""


@app.command
def advance_phase() -> CommandOutcome:
    """Advance ``phase.current`` to the next member; refuse skips with exit 3."""
```

The Cyclopts function-name → kebab command-name mapping (`set_cursor` →
`set-cursor`, `advance_phase` → `advance-phase`) is automatic at 4.18.0
(verified in Verified Facts) and is pinned by a command-name test; the
`set-cursor` and `advance-phase` *command* names are load-bearing (the harness
invokes them) and are asserted, not assumed. `build_app` stays zero-argument;
its existing `check` subcommand is unchanged.

Re-export any new public name from `novel_ralph_skill/state/__init__.py`
(`build_initial_document`) and update `__all__`. The mutator subcommand bodies
reuse the existing `STATE_INPUT_ERRORS`, `WORKING_DIR_NAME`, `CommandOutcome`,
`StateInputError`, `ExitCode`, `validate_state`, `load_document`,
`document_to_state`, and `write_document_atomically`, and add the **two new**
helpers `_load_document_or_state_error` (document-load faults) and
`_state_view_or_state_error` (typed-view faults from a valid-but-incomplete
document); the mutators never call bare `document_to_state` (BR2-1). They do
**not** reuse `_load_or_state_error` (it returns a `State`, not a
`TOMLDocument`).

## Revision note

Round 2 (2026-06-23, planning agent). Resolved the four round-1 design-review
blocking points, all pinned by source reads and empirical checks against the
locked libraries in this worktree:

- **B1** — work item 2 now enumerates the **full** required table set
  field-by-field against `state/parse.py` (including `[drafting.critic].pass`,
  `last_finding_counts{blocker,major,minor,taste}`,
  `[drafting.fangirl].last_chapter_passed`, all `[gates.*]` booleans,
  `[word_counts].current` and a **present empty** `by_chapter`, and
  `[novel].created_at`), and the unit test asserts `parse_state(...)`
  **succeeds** before any field assertion (Decision Log D5, Risk "init builds
  an unreadable document").
- **B2** — the mutators load via a new `_load_document_or_state_error` →
  `load_document` (tomlkit), not `_load_or_state_error` → `load_state`
  (tomllib); the existing `STATE_INPUT_ERRORS` tuple is shown (empirically) to
  already subsume every document-path fault (`ParseError`/`UnexpectedCharError`/
  `UnexpectedEofError` are `ValueError`s; `NonExistentKey` is a `KeyError`;
  `read_text` raises `OSError`), so it needs no extension, and a unit test
  re-pins the two `issubclass` facts (Decision Log D4, Constraint "Mutator load
  path").
- **B3** — work item 4 names the concrete, buildable corpus tree
  `INCOHERENT_VARIANTS["completed-prefix-gap"]` for the out-of-order BDD
  scenario, states explicitly that the refusal guards against advancing **from
  an already-incoherent prior state** (since `advance_phase()` cannot skip),
  adds an explicit prior-state coherence guard (step 2), and names the exact
  violated invariant (`completed-prefix`) — reconciling with design §3.2/§4.1
  wording (Decision Log D7, Risk-free via the empirical pin).
- **B4** — the into-`drafting` success case is built from an **explicitly
  constructed** populated-manifest `chapter-planning` tree via
  `make_working_tree_spec`/`build_tree` (`phase_current="chapter-planning"`,
  `phase_completed=PHASE_ORDER[:7]`, non-empty `chapters=` with
  `draft_words=0`), confirmed empirically to advance into a coherent `drafting`
  state; `PHASE_STATES["chapter-planning"]` is explicitly disqualified (empty
  manifest) (Decision Log D6).

Advisories addressed: A1 (init-overwrite reading surfaced as a decision, not a
derivation), A2 (`created_at` explicitly excluded from the unit-test equality),
A3 (the `set-cursor` Hypothesis property promoted to expected), A5 (append
round-trip assertion added).

Round 3 (2026-06-23, planning agent). Resolved the two round-2 design-review
blocking points, both verified against source in this worktree:

- **BR2-1** — the typed-view derivation no longer escapes the exit-3 channel. A
  **second** new helper `_state_view_or_state_error(document) -> State` wraps
  `document_to_state` under the same `STATE_INPUT_ERRORS` tuple, and
  `set-cursor` (step 4) and `advance-phase` (steps 1 and 6) call it instead of
  bare `document_to_state`. The fact that `contract/runner.py:run` catches only
  `CycloptsError`/`StateInputError` (so any other exception exits `1`) is
  pinned in Verified Facts ("runner.run catch arms") by reading the source. New
  tests: a contract test driving `set-cursor` and `advance-phase` against
  `working/state.toml = "schema_version = 1\n"` (valid TOML, missing required
  tables) asserting exit `3` not `1`, and a `_state_view_or_state_error` unit
  test over an incomplete document and a bad-phase-string document. Constraint
  "Typed-view derivation is also exit-3-routed" and Decision Log D8 record it.
- **BR2-2** — `init` now creates the full Initialisation directory skeleton
  `working/{characters,world,reader,plan,manuscript,reviews}` (sourced verbatim
  from state-layout.md "Initialisation" step 1, read in this worktree),
  matching its cited source of truth rather than silently diverging. A
  work-item-2 test asserts the six subdirectories and `log.md` exist after
  `init`. The Decision Log records the decision and rationale.

Advisories addressed in round 3: AR2-1 (the developers-guide subsection states
plainly that, because `advance-phase` takes no argument, "refuses out-of-order
completion" is realised solely as the prior-state coherence guard and no
skip-rejection logic exists), AR2-2 (the `set-cursor` success test pins the
exact in-range cursor `chapter=2, scene=0, beat=0`). Status: DRAFT, pending
design review (round 3).

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
post-merge audit (`docs/issues/audit-2.2.2.md`). Execute each as a small
addendum pass — no plan or design-review cycle: make the change, run `make all`
(plus `make markdownlint`/`make nixie` for Markdown), `coderabbit review
--agent`, commit, and tick the matching roadmap sub-task on merge. The
substantial, cross-cutting findings were re-routed off this task: the mutator
success-result vocabulary (audit Finding 2) to roadmap step 1.3 (task 1.3.5),
and the partial-`init` bootstrap recovery (review:2.2.2) to step 2.3
(task 2.3.4); the doc gap below is the small fix.

- [x] 2.2.2.1 — Document the `init`, `set-cursor`, and `advance-phase`
  subcommands in the users' guide (from audit:2.2.2, high). Task 2.2.2 promoted
  three subcommands from stubs to shipping commands but updated only the
  developers' guide; `docs/users-guide.md` lines 92–128 still describe only
  `novel-state check`. Extend the `novel-state` section with a subcommand each:
  `init` (its `--title`/`--slug`/`--target-word-count` options, the directory
  skeleton it creates, and the exit-`3` refusal to overwrite an existing
  `state.toml`), `set-cursor` (its three integer options and the
  `cursor-coherent` refusal), and `advance-phase` (its zero-argument advance, the
  terminal-`done` refusal, and the empty-manifest-into-`drafting` refusal). State
  the shared validate-before-persist, exit-`3` refusal, write-nothing contract
  once and reference it from each. Gate with `make markdownlint` and `make
  nixie`.
- [x] 2.2.2.2 — Route `_check`, `init`, and the two mutators through a single
  `working/state.toml` path accessor (from audit:1.3.5, low; re-surfaced from
  audit:2.2.2 Finding 3). The canonical path is constructed in three places —
  `commands/novel_state.py` `_check` (`pathlib.Path(WORKING_DIR_NAME) /
  "state.toml"`) and `init` (`working / "state.toml"`), and
  `commands/_state_mutators.py` `_state_path` — so promote one accessor (reusing
  the existing `_state_path` or a shared `WORKING_DIR_NAME`-anchored helper) and
  route all four call sites through it, removing the triplicated path
  construction without changing behaviour. Gate with `make all`.
- [ ] 2.2.2.3 — Correct the partial-`init` direction in this plan's Decision Log
  D3 (from review:2.3.4, low). D3 describes the realisable partial-`init` as
  `log.md` present and `state.toml` absent, but `init` writes `state.toml` first,
  so the realisable case is the inverse (`state.toml` present, `log.md` absent),
  the direction task 2.3.4 actually targets and reconciles. D3 was intentionally
  left untouched as out of scope when 2.3.4 landed; correct the stale D3 prose
  here so this plan's Decision Log agrees with the implemented direction. Gate
  with `make markdownlint` and `make nixie`.
