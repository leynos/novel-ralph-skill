# Implement the `tomlkit` round-trip and atomic write helper

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

This plan delivers the lossless write half of the `novel-state` slice: a small
module that reads `working/state.toml`, lets a caller mutate it, and writes it
back through `tomlkit` so the file's hand-authored comments and deliberate
layout survive every turn (design §5.3; ADR-002). The same module supplies the
crash-safe write discipline every mutator in the spine inherits — a temporary
file in the target directory followed by `Path.replace` (atomic on POSIX,
design §3.4) — and the `[pending_turn]` intent record that turns a torn
multi-file turn from a silent corruption into a declared, inspectable state
(design §3.4).

After this change a developer (and every later mutator: `init`, `set-cursor`,
`advance-phase`, `recount`, `reconcile`) can:

1. Round-trip `state.toml` losslessly. Reading a `state.toml`, applying a no-op
   edit, and writing it back leaves the file byte-for-byte identical, comments
   and whitespace included. A targeted value change rewrites only the bytes of
   the value it touched and leaves every comment intact.
2. Write atomically. A write that crashes after the temporary file is created
   but before the rename leaves the prior coherent `state.toml` intact; no torn
   file is ever observable at the live path.
3. Bracket a multi-file turn with intent. A caller opens a `[pending_turn]`
   record naming the operation and the paths it will write before touching any
   other file, and clears it only after every artefact is written and verified;
   a write that dies mid-turn leaves a populated `[pending_turn]` for the next
   turn's `novel-state check`/`reconcile` (roadmap task 2.3.2) to read.

The observable outcome is a property-based test demonstrating the round-trip
property — a no-op mutate-and-write is byte-for-byte stable, and a surgical
value mutation rewrites only the touched value while preserving every comment —
exercised over a *comment-and-layout-bearing* `state.toml` fixture (block
comments, inline comments, blank-line layout, and an array-of-tables form), so
the property genuinely guards ADR-002 Functional requirement 1's "including
comments and whitespace" clause and the design §9 "a no-op `recount` preserves
formatting and comments" criterion. The comment-free corpus sweep runs as an
additional case, never as the sole carrier of the guarantee. A behavioural test
demonstrates that a write interrupted before the rename leaves a populated
`[pending_turn]` record and an untorn prior file.

This task delivers the *helper*, not the subcommands. `init`, `set-cursor`, and
`advance-phase` are roadmap task 2.2.2; `recount` is 2.3.1; `check`/`reconcile`
are 2.3.2. This plan exposes the seams those tasks call into and no Cyclopts
wiring of its own. It depends on roadmap tasks 1.1.2 (tomlkit dependency, DONE)
and 2.1.1 (typed schema and phase enum, DONE).

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **`tomlkit` is the only sanctioned writer.** State serialization reads,
  mutates, and re-writes through `tomlkit` (ADR-002; design §5.3). Do not add
  `tomli_w`, a hand-built serializer, or any `tomllib`-plus-side-channel writer.
  `tomllib` may still be used for read-only decode where formatting does not
  matter (it already backs `load_state`), but every *write* goes through
  `tomlkit`.
- **Atomic write discipline.** Every write is a temporary file created in the
  *target directory* followed by `Path.replace` (design §3.4;
  `docs/scripting-standards.md` "Reading / writing files and atomic updates").
  The temp file must share the target's directory so the rename stays on one
  filesystem and is atomic. No in-place `open(path, "w")` write of `state.toml`.
- **`[pending_turn]` brackets multi-file work.** The intent record is opened
  *before* any other file is touched and cleared *after* every artefact is
  written and verified (design §3.4, §5.1). Both the open and the clear use the
  same atomic discipline.
- **No narrative judgement, no validation here.** This helper is mechanical
  (ADR-001; design §1). It does not enforce the §5.2 invariants — that is the
  `check` validator (roadmap task 2.1.2). It moves bytes and structure; it does
  not decide whether a state is coherent.
- **Read-only typed model is untouched.** `novel_ralph_skill/state/schema.py`,
  `phase.py`, and `parse.py` stay read-only structural code (their module
  docstrings promise "no writing"). The writer is a *new* module; do not bolt
  writing onto `parse.py`.
- **Package targets and gates.** The new module lives under
  `novel_ralph_skill/` and is in `$(PYTHON_TARGETS)`, so it carries 100%
  `interrogate` docstring coverage, passes Ruff lint and format, Pylint, and
  `ty`. No code file exceeds 400 lines (AGENTS.md). `requires-python = ">=3.14"`
  (`pyproject.toml`), so 3.14 language features are available; do not gate on
  3.13.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, docstrings,
  comments, and commit messages (AGENTS.md; `en-gb-oxendict`).
- **No shell-out.** v1 commands invoke no external process (design §4), so this
  helper does not use `cuprum`. Filesystem work uses `pathlib` and `tempfile`
  only. (Verified against design §4 line 241: "None invokes an external process
  for its core logic, so cuprum is required only where a command shells out
  (none do in v1).")

## Tolerances (exception triggers)

Stop and escalate when any of these is breached rather than working around it.

- **Scope.** If the change requires touching more than 10 files or ~550 net new
  lines of code, stop and re-scope. The expected file set is: the writer module
  (`novel_ralph_skill/state/document.py`), its `__init__.py` re-export, the
  writer test module (`tests/test_state_document.py`), the `pytest-bdd`
  dependency guard (`tests/test_pytest_bdd_dependency.py`), the torn-turn
  `.feature` file and its `tests/steps/` step module, `pyproject.toml` and
  `uv.lock` (the `pytest-bdd` addition), and `docs/developers-guide.md` — about
  nine files. (The earlier six-file budget predated the work-item-3
  `pytest-bdd` dependency step and its guard/feature/step files; round-2 review
  B4.)
- **Interface.** If delivering the round-trip forces a change to the public
  signature of `parse_state`, `load_state`, or any `state/schema.py` dataclass,
  stop and escalate — those are the 2.1.1 contract other tasks depend on.
- **Dependencies — runtime.** If a new *runtime* dependency beyond the locked
  `tomlkit` (0.15.0, `uv.lock`) and `cyclopts` (the `[project].dependencies`
  set, `pyproject.toml` line 8) is required, stop and escalate. ADR-002 fixes
  the runtime dependency set and this helper ships no new runtime import.
- **Dependencies — dev/test.** A new *dev/test* dependency under
  `[dependency-groups].dev` is permitted only when AGENTS.md already mandates
  it. AGENTS.md line 143 mandates `pytest-bdd` for behavioural tests, and this
  plan is the first behavioural test in the suite, so adding `pytest-bdd` to
  `[dependency-groups].dev` (work item 3) is a *sanctioned* dev-tooling
  addition, not a forbidden runtime dependency — it is a named work-item step
  with a version-pin guard, never an implicit side effect (round-2 review B4).
  Any dev/test dependency *not* mandated by AGENTS.md still trips this trigger:
  stop and escalate.
- **Round-trip leakage.** If the byte-for-byte no-op property fails on any
  corpus state file even once under Hypothesis, stop: the cause is either a
  corpus file `tomlkit` cannot losslessly round-trip (a corpus defect to raise)
  or a helper that re-serializes through the typed model (a design error in
  this plan). Do not weaken the property to make it pass.
- **Iterations.** If the property or behavioural suite still fails after 3
  focused attempts, stop and document the blocker in the Decision Log.
- **Ambiguity.** If `tomlkit`'s structural-edit behaviour (table insertion or
  removal whitespace) makes the `[pending_turn]` open/clear cycle unable to
  restore a settled file byte-for-byte, stop and escalate with the trade-offs
  (see Risk "pending_turn whitespace").

## Risks

- Risk: `tomlkit` table insertion/removal introduces stray whitespace.
  Severity: medium. Likelihood: high (observed empirically — see Surprises &
  Discoveries). Mitigation: scope the byte-for-byte property to *no-op value*
  round-trips and *surgical value mutation*, which the official docs and the
  empirical probe both confirm are exact. Treat the `[pending_turn]` open/clear
  cycle as a *structural* change whose guarantee is "the prior settled file is
  recoverable", asserted at the value/parsed-equality level (the cleared
  document re-parses to a `State` equal to the original and carries no
  `[pending_turn]`), not byte-for-byte. The round-trip property (work item 2)
  and the clear-restores property (work item 3) are deliberately different
  strengths for this reason.
- Risk: the locked `tomlkit` is 0.15.0 but the developer's ambient interpreter
  may carry a different version. Severity: low. Likelihood: medium. Mitigation:
  run the suite through the project's `uv`-resolved environment (`make test`),
  which uses `uv.lock`'s 0.15.0; do not rely on the ambient `python3`. The
  round-trip property test is itself the guard ADR-002's "Known risks" names
  against a silent `tomlkit` major-version regression. The empirical probe in
  "Artifacts and notes" was re-run under the `uv`-resolved 0.15.0 environment
  (not an ambient interpreter), so the mechanism is verified at the version
  that ships.
- Risk: the byte-for-byte property guards nothing because its input has no
  comments to lose. Severity: high. Likelihood: high if unaddressed (the corpus
  `state.toml` files are built programmatically by
  `tests/working_corpus/_builder._build_state_document` via `tomlkit.table()` /
  `inline_table()` and carry zero comments and no hand-authored layout). A
  no-op property over comment-free, tomlkit-emitted files proves only that
  `parse → dumps` is identity on tomlkit's own output; it would stay green even
  if the writer silently stripped comments or reflowed layout. Mitigation: the
  round-trip *property* (work item 1/2) and the surgical-mutation *property*
  (work item 2) both draw over a hand-authored, comment-and-layout- bearing
  `state.toml` fixture, so the byte-for-byte assertions actually constrain
  comment and whitespace preservation (B1/B2 from the round-1 review). The
  comment-free corpus sweep is retained as an additional case only.
- Risk: a crash-mid-write test that genuinely kills the process is not portable
  or deterministic under `pytest-xdist`. Severity: medium. Likelihood: medium.
  Mitigation: simulate the interruption deterministically — inject a failure
  *between* writing the `[pending_turn]` record (its own atomic write) and the
  final clear, by raising inside the caller's artefact step, then assert on the
  on-disk state. Do not fork or signal a real process.
- Risk: the atomic temp file leaks into the working directory on the error path.
  Severity: low. Likelihood: medium. Mitigation: write the temp file with a
  recognisable prefix in the target directory and unlink it on any failure
  before `Path.replace`; assert no stray temp file survives a failed write.
- Risk: re-serializing through the typed `State` (which is lossy) instead of the
  `tomlkit` document. Severity: high. Likelihood: low. Mitigation: the helper
  holds the live `tomlkit.TOMLDocument`; `parse_state` is used only to *read*
  the typed view for callers, never as the write source. The constraint and the
  round-trip property both guard this.

## Progress

- [x] Work item 1: add the hand-authored comment-and-layout-bearing
  `state.toml` fixture, scaffold the `state/document.py` writer module, and add
  a failing round-trip property test over that fixture (red). **Done**: the
  fixture `COMMENT_BEARING_STATE_TOML` and a Hypothesis no-op round-trip
  property (plus a corpus-sweep case) live in `tests/test_state_document.py`,
  both `xfail(strict, raises=NotImplementedError)` against the
  `write_document_atomically` stub. The property uses a per-input
  `tempfile.TemporaryDirectory` rather than the function-scoped `tmp_path`
  fixture, to satisfy Hypothesis's function-scoped-fixture health check. Gate
  green at 160 passed, 2 xfailed.
- [x] Work item 2: implement the lossless `tomlkit` read-mutate-write
  round-trip (green) and the atomic temp-file-plus-`Path.replace` write, with
  the no-op and surgical-mutation comment-preservation properties over the
  comment-bearing fixture. **Done**: `write_document_atomically` writes a
  `NamedTemporaryFile` (prefix `.state.toml.`) in `path.parent`, then
  `Path.replace`s it over the target, unlinking the temp file on any `OSError`
  before the rename. The `xfail` markers are gone; the no-op and corpus
  properties pass green. Added a surgical-mutation Hypothesis property
  (string-replacement oracle over `word_counts.current`) and three atomic-write
  unit tests: dumps-equality, the temp file lives in `path.parent` (via a
  `Path.replace` spy, not a `NamedTemporaryFile` spy — `ty` cannot match the
  factory's overloads through `*args`), and a forced-rename-failure leaving the
  prior file untorn with no stray temp file. Gate green at 166 passed.
- [x] Work item 3: add `pytest-bdd` to `[dependency-groups].dev` (regenerate
  `uv.lock`, add a version-pin guard); implement the `[pending_turn]`
  open/clear bracket (the yielded document is the single clean-exit write
  source) and the interrupted-write recovery behaviour, with the torn-turn
  behavioural scenario expressed in `pytest-bdd`. **Done in two commits**: (a)
  the dependency step added `pytest-bdd>=8.1.0` (resolved 8.1.0) and the
  version-pin guard `tests/test_pytest_bdd_dependency.py`; (b) the behaviour
  implemented `open_pending_turn`, `clear_pending_turn`, and the `pending_turn`
  context manager (writes the record atomically before yielding, clears and
  re-writes the *yielded* document on clean exit, leaves it populated on an
  exception). Tests: the torn-turn `pytest-bdd` scenario
  (`tests/features/torn_turn.feature` + `tests/steps/torn_turn_steps.py`, bound
  by `tests/test_torn_turn_bdd.py`), a clear-restores parsed-equality test, a
  schema round-trip test, the A1 in-bracket-value-survives test, an
  idempotent-clear test, and a record-persisted-before-yield test. Gate green at
  174 passed.
- [x] Work item 4: export the helper's public surface, update the developers'
  guide, and run the full gate (`make all`; `make markdownlint`; `make nixie`).
  **Done**: `novel_ralph_skill/state/__init__.py` re-exports the six writer
  names (`load_document`, `document_to_state`, `write_document_atomically`,
  `open_pending_turn`, `clear_pending_turn`, `pending_turn`) and its module
  docstring no longer says writing is "task 2.2.1" pending. The developers'
  guide gains a "`document.py` round-trip writer" subsection. The state-layout
  direct-edit guard passes unchanged (no hand-edit recipe added).

## Surprises & discoveries

- Observation (work item 1): a Hypothesis `@given` property cannot use the
  function-scoped `tmp_path` fixture — Hypothesis raises `FailedHealthCheck`
  because the fixture is not reset between generated inputs. Impact: the no-op
  round-trip property creates a fresh `tempfile.TemporaryDirectory` per input
  instead. The corpus-sweep case (not a `@given` property) keeps its fixture.
- Observation (work item 1, coderabbit): en-GB Oxford spelling mandates `-ize`
  forms (`serialize`, `serialization`), which the new prose now uses. The
  surrounding legacy modules (`parse.py`, `envelope.py`, `_freeze.py`) still
  carry `-ise` spellings; this task does not mass-rewrite them — only the new
  `document.py`, the new tests, and this execplan adopt Oxford spelling, to
  avoid an unrelated sweep. Decision recorded in the Decision log.
- Observation: `tomlkit` table *insertion then removal* is not byte-for-byte
  reversible. Evidence: adding a `[pending_turn]` table via
  `doc["pending_turn"] = tomlkit.table()`, dumping, re-parsing, and
  `del doc["pending_turn"]` produced a file 1 byte longer than the original (a
  residual blank line) — **re-confirmed under the `uv`-resolved tomlkit
  0.15.0** (507 vs 506 bytes; the locked, shipped version, not the earlier
  0.14.0 ambient run). Impact: the `[pending_turn]` open/clear cycle's recovery
  guarantee is asserted at parsed-`State` equality, not byte-for-byte; the
  byte-for-byte property is reserved for no-op and surgical *value* edits,
  which are exact. Recorded as the Risk "pending_turn whitespace" and shapes
  work items 2 and 3.
- Observation: `tomlkit.parse(s)` then `tomlkit.dumps(doc) == s` holds exactly,
  and `doc["word_counts"]["current"] = N` rewrites only the value's bytes and
  preserves both block and inline comments. Evidence: empirical probe **re-run
  under the `uv`-resolved tomlkit 0.15.0** on a hand-authored
  comment-and-layout- bearing `state.toml` (block comments, an inline
  `# String`-style comment on a value, blank-line layout, an inline
  `by_chapter` table, and an array-of-tables `[[chapters]]`): no-op identical
  `True`; surgical `word_counts.current` mutation byte-equal to a
  string-replace of the old value `True`; both the block comment and the
  running-total inline comment survive the mutation. The official 0.15.0-series
  quickstart confirms the same mechanism (`assert dumps(doc) == content` and the
  `doc["table"]["baz"] = 13` modify preserving the `# String` comment).
  Impact: confirms the round-trip mechanism this plan pins, at the shipped
  version, over comment-bearing input — the B1/B2/B3 fixes.
- Observation: the corpus `state.toml` files carry **zero comments and no
  hand-authored layout** — they are built by
  `tests/working_corpus/_builder._build_state_document` (lines 134-154) from
  `tomlkit.table()` / `inline_table()` / `array()` with no comment insertion
  anywhere in the builder. A byte-for-byte property over those files cannot
  guard comment preservation. Impact: a hand-authored comment-bearing fixture
  is the primary property input; the corpus sweep is an additional case (B1/B2).

## Decision log

- Decision: place the writer in a new module
  `novel_ralph_skill/state/document.py` rather than extending `parse.py`.
  Rationale: `parse.py` and the whole `state` package promise read-only
  structural parsing in their docstrings; writing is a distinct responsibility
  (AGENTS.md "clear file boundaries", "group by feature"). Keeping the writer
  separate preserves the 2.1.1 read-only contract and keeps both modules under
  the 400-line cap. Date/Author: 2026-06-22, planning agent.
- Decision: the helper operates on the live `tomlkit.TOMLDocument`, exposing the
  typed `State` (via `parse_state` over the document's plain mapping) only as a
  read view for callers. Rationale: re-serializing from the lossy typed model
  would defeat ADR-002. The document is the source of truth for bytes; `State`
  is the source of truth for typed reads. Date/Author: 2026-06-22, planning
  agent.
- Decision: simulate the crash-mid-write deterministically (inject a failure
  between the `[pending_turn]` open and the clear) rather than forking or
  signalling a process. Rationale: portability and `pytest-xdist` determinism
  (Risk "crash-mid-write"); the contract being tested is on-disk state after an
  interruption, which a controlled raise reproduces faithfully. Date/Author:
  2026-06-22, planning agent.
- Decision: no `cuprum` and no `cmd-mox` in this task. Rationale: the helper
  shells out to nothing (design §4); cuprum is required only where a command
  invokes an external process, and none do in v1. The suite touches only the
  filesystem under `tmp_path`, matching design §9's "v1 commands shell out to
  nothing, so the suite touches only the filesystem". Date/Author: 2026-06-22,
  planning agent.
- Decision: the round-trip and surgical-mutation **properties** draw over a
  hand-authored comment-and-layout-bearing `state.toml` fixture, defined as a
  module-level constant in `tests/test_state_document.py`, not over the
  comment-free corpus alone. Rationale: the corpus carries no comments
  (verified in `_builder._build_state_document`), so a byte-for-byte property
  over it guards nothing of ADR-002 Functional req 1's "including comments and
  whitespace" (round-1 review B1/B2). The fixture carries block comments, an
  inline value comment, blank-line layout, an inline table, and an
  array-of-tables. The comment-free corpus sweep is retained as an additional
  case. The fixture is kept test-local rather than added to the
  `working_corpus` builder because the corpus builder's contract (a
  programmatic, comment-free tree consumed by the structural oracle and the
  2.1.2 validator) deliberately does not author comments; a comment-bearing
  variant belongs to the writer's own round-trip suite, not the
  structural-coherence corpus. Should 2.2.2/2.3.x need the same fixture,
  promote it to a shared `tests/` module then. Date/Author: 2026-06-22,
  planning agent.
- Decision: the `pending_turn` bracket's clean-exit write re-dumps the
  **yielded,
  caller-mutated** `TOMLDocument`, never a reloaded fresh copy. Rationale: a
  real mutator (e.g. `recount`, task 2.3.1) edits state *values* on the yielded
  document inside the bracket; reloading before the clear would silently
  discard those edits (round-1 review A1). The yielded document is therefore
  the single write source for the clean-exit write, and a test pins that an
  in-bracket value edit survives a clean exit. Date/Author: 2026-06-22,
  planning agent.
- Decision: introduce `pytest-bdd` as the project's first behavioural-test
  dependency under `[dependency-groups].dev`, as a named step in work item 3,
  rather than rewriting the torn-turn scenario on bare `pytest`. Rationale:
  round-2 review B4. The plan mandates a behavioural test for the torn-turn
  recovery flow, and AGENTS.md line 143 mandates `pytest-bdd` for behavioural
  tests; `pyproject.toml` already anticipates a `tests/steps/*.py` step
  directory (line 97 per-file-ignores), so this is the sanctioned form, not a
  smuggled addition. The competing option — express the Given/When/Then as a
  plain `pytest` function and drop `pytest-bdd` — was rejected because it
  deviates from AGENTS.md line 143 for no gain: `pytest-bdd` is the standard
  behavioural runner the suite will need from 2.2.2 onward, so paying the
  one-time introduction cost here is correct. The dependency Tolerance is
  amended (see "Dependencies — dev/test") to distinguish a forbidden runtime
  dependency from a dev/test dependency AGENTS.md mandates, so the implementer
  does not stop-and-escalate on a routine, sanctioned addition (round-2
  pre-mortem). The addition carries a version-pin guard mirroring
  `tests/test_contract_test_deps.py` / `tests/test_tomlkit_dependency.py`, so a
  silent `uv` re-resolution trips the guard while a deliberate upgrade updates
  the pin visibly. Date/Author: 2026-06-22, planning agent.
- Decision: this task owns only the *producer* side of `[pending_turn]` —
  writing the record on bracket entry and leaving it populated on an
  interrupted turn. The §5.4 rollback path ("clears the `[pending_turn]` record
  and leaves `state.toml` at the prior coherent point") is `reconcile`'s job
  (task 2.3.2), not this helper's. Rationale: round-1 review A2 — signpost the
  boundary so a reviewer does not mistake the absent rollback path for a gap.
  The "clear-restores" property (parsed-equality) covers the clean-exit clear
  only. Date/Author: 2026-06-22, planning agent.
- Decision (work item 3, implementation): the `pending_turn` generator leaves
  its `yield` unprotected (no `try`/`finally`), so the clear-and-write runs only
  on a clean exit. Ruff's preview rule RUF075 ("fallible-context-manager")
  flags this and advises wrapping the `yield`; that advice is wrong here — a
  `finally` would clear the record on the error path, which is the exact
  opposite of the design §3.4 leave-on-error contract. Suppressed with a
  narrow `# noqa: RUF075` and a comment citing §3.4/§5.4. Date/Author:
  2026-06-22, implementing agent.
- Decision (work item 3, implementation): the step module lives in a
  `tests/steps/` package (`__init__.py` added, mirroring
  `tests/working_corpus/`), and the scenario binder `tests/test_torn_turn_bdd.py`
  star-imports it (`from steps.torn_turn_steps import *`) so `pytest-bdd`'s
  `scenarios()` discovers the step callables in the binder's namespace.
  Rationale: `tests/` is on `sys.path` (the corpus is imported the same way), so
  a `steps` package resolves; the directory is already exempt from the
  assert/argument-count rules (`pyproject.toml` line 97). Date/Author:
  2026-06-22, implementing agent.
- Decision (work item 3, coderabbit): CodeRabbit's R503 finding (add explicit
  `return` to the `-> None` step functions) was skipped. Ruff's enabled `RET`
  rules do not require it for void functions, and a redundant trailing `return`
  would itself be flagged. Date/Author: 2026-06-22, implementing agent.

## Outcomes & retrospective

All three purpose outcomes are delivered and gate-green:

- **Lossless round-trip.** A no-op load-and-write is byte-for-byte stable and a
  surgical `word_counts.current` edit rewrites only the touched value — both
  pinned by Hypothesis properties over the comment-and-layout-bearing fixture
  (and a corpus-sweep breadth case), at the locked tomlkit 0.15.0.
- **Atomic write.** `write_document_atomically` writes a temp file in the
  target's directory and `Path.replace`s it; a forced rename failure leaves the
  prior file untorn with no stray temp file (unit-tested).
- **`[pending_turn]` bracket.** The context manager writes the record before
  yielding, leaves it populated on an exception (the torn-turn `pytest-bdd`
  scenario), and clears it on a clean exit while preserving an in-bracket value
  edit (the A1 test).

Gaps the later mutator tasks must absorb (all signposted, none a defect here):

- **§5.4 rollback.** This task ships only the *producer* side of
  `[pending_turn]`. Reading an uncleared record, comparing the named paths
  against disk, and rolling `state.toml` back to the prior coherent point is
  `reconcile`'s job (task 2.3.2). The clear-restores property covers only the
  clean-exit clear (parsed-equality, not byte-for-byte, because tomlkit
  table insertion-then-removal can leave a residual blank line).
- **No validation.** The writer enforces no §5.2 invariant; `novel-state check`
  (task 2.1.2) does. `write_document_atomically` will persist an incoherent
  document if a caller hands it one — coherence is the caller's contract.
- **CLI wiring.** `init`, `set-cursor`, `advance-phase` (task 2.2.2) and
  `recount` (task 2.3.1) wire these seams into Cyclopts command bodies; the
  exit-code contract is exercised there, not here.

Retrospective notes for the next implementer: (1) Hypothesis `@given` cannot use
the function-scoped `tmp_path` fixture — use a per-input
`tempfile.TemporaryDirectory`. (2) The `pending_turn` generator's unprotected
`yield` is load-bearing (leave-on-error) and trips preview rule RUF075; the
`# noqa` is justified, not a smell. (3) `make fmt` rewrites unrelated Markdown
docs (a known repo quirk); format only the touched files with `ruff format
<paths>` and run `markdownlint-cli2 <file>` per touched doc instead of the
whole-tree `make markdownlint`/`make fmt`.

## Context and orientation

The reader needs no prior plan. The relevant facts:

The harness's primary on-disk memory is `working/state.toml`, a TOML file with
hand-authored comments and a deliberate layout a human reads during recovery
(design §5.3; ADR-002 "Context"). The typed, *read-only* model already exists
in the `novel_ralph_skill.state` package (roadmap task 2.1.1, DONE):

- `novel_ralph_skill/state/schema.py` — frozen, slotted, keyword-only
  dataclasses mirroring each `state.toml` table: `State` and its sub-shapes
  `NovelMeta`, `PhaseState`, `ChapterEntry`, `Drafting`, `CriticState`,
  `FindingCounts`, `FangirlState`, `Gates`, `KnittingGates`, `FinalGate`,
  `WordCounts`, and `PendingTurn`.
- `novel_ralph_skill/state/phase.py` — the closed eleven-member `Phase` enum and
  `PHASE_ORDER`.
- `novel_ralph_skill/state/parse.py` — `parse_state(mapping) -> State` (a pure
  structural parse over a decoded mapping) and `load_state(path) -> State` (a
  thin `tomllib`-backed file read). Both are read-only and enforce no §5.2
  invariant. The module docstring explicitly defers the round-trip to "task
  2.2.1".
- `novel_ralph_skill/state/__init__.py` — re-exports the above.

What does *not* yet exist is any code that *writes* `state.toml`. That is this
task. The contract every command shares (the JSON envelope, exit codes, and the
`run` wrapper) lives in `novel_ralph_skill/contract/` (roadmap task 1.3.1,
DONE) and is *not* in scope here — this helper has no CLI; it is a library seam
the mutator subcommands (2.2.2, 2.3.x) will call from inside their command
bodies.

The shared on-disk test corpus lives in `tests/working_corpus/` (roadmap task
1.3.2) and is consumed through the registered fixtures in
`tests/corpus_fixtures.py` (developers-guide "The `working/` fixture corpus").
The corpus writes its `state.toml` files through `tomlkit`
(`tests/working_corpus/_builder.py`, which imports `tomlkit` and builds
tables), so corpus state files are valid `tomlkit` round-trip inputs — **but
they carry no comments and no hand-authored layout** (the builder calls
`tomlkit.table()` / `inline_table()` / `array()` and never inserts a comment),
so they cannot by themselves test comment preservation (round-1 review B1/B2).
The corpus fixtures are **factory callables**, not bare `Path` fixtures:
`phase_state_tree` returns `(phase: str) -> Path`, `baseline_tree` returns
`() -> Path`, and `coherent_oracle_cases` returns a
`list[tuple[WorkingTreeSpec, Path]]`. Each returned `Path` is the `working/`
directory; the state file is at `working_dir / "state.toml"`, so a test reads
its bytes with `(working_dir / "state.toml").read_text(encoding="utf-8")`.
Comment preservation is therefore tested against a separate hand-authored
comment-and-layout-bearing `state.toml` fixture defined in the writer's own
test module (see the Decision log).

Terms used in this plan:

- **Round-trip / lossless.** Read a `state.toml` into a `tomlkit` document,
  optionally edit values, and write it back so comments and layout survive. A
  *no-op* round-trip reads and writes with no edit; the file is byte-for-byte
  identical.
- **Atomic write.** Write new contents to a temporary file in the target's
  directory, then `Path.replace` the temp file over the target. On POSIX the
  rename is atomic, so a reader sees either the whole old file or the whole new
  file, never a torn half.
- **`[pending_turn]` intent record.** A small table in `state.toml` naming the
  operation in flight and the paths it will write, present only while a
  multi-file mutation is mid-write and cleared once every artefact is verified
  (design §3.4; `PendingTurn` in `schema.py`).

## Interfaces and dependencies

Use the locked `tomlkit` (0.15.0, `uv.lock`), `pathlib`, and `tempfile` from
the standard library. No new *runtime* dependency, no `cuprum`/`cmd-mox`. The
module under `novel_ralph_skill/` adds no import beyond `tomlkit` and the
standard library, so `[project].dependencies` (`cyclopts`, `tomlkit`) is
unchanged.

This task does add exactly one *dev/test* dependency: `pytest-bdd`, the
behavioural-test runner AGENTS.md line 143 mandates and which the project does
not yet carry (it is absent from `[dependency-groups].dev` and `uv.lock`, and no
`.feature` file or `from pytest_bdd` import exists in `tests/`). It enters
under `[dependency-groups].dev` as a named step in work item 3, with `uv.lock`
regenerated and a version-pin guard mirroring
`tests/test_contract_test_deps.py` and `tests/test_tomlkit_dependency.py`. It
is a behavioural-test tool, never a runtime import of `novel_ralph_skill`. See
the Tolerances "Dependencies — dev/test" carve-out (round-2 review B4).

Create `novel_ralph_skill/state/document.py` exposing at least:

```python
# novel_ralph_skill/state/document.py
from __future__ import annotations

import collections.abc as cabc
import contextlib
from pathlib import Path

import tomlkit
from tomlkit import TOMLDocument

from novel_ralph_skill.state.schema import State


def load_document(path: Path) -> TOMLDocument:
    """Read ``state.toml`` into a style-preserving ``tomlkit`` document."""


def document_to_state(document: TOMLDocument) -> State:
    """Parse the typed read view from a ``tomlkit`` document (delegates to
    :func:`novel_ralph_skill.state.parse.parse_state`)."""


def write_document_atomically(document: TOMLDocument, path: Path) -> None:
    """Serialise ``document`` and write it to ``path`` via a temp file in the
    target directory followed by ``Path.replace`` (design §3.4)."""


def open_pending_turn(
    document: TOMLDocument, *, operation: str, paths: cabc.Sequence[str]
) -> None:
    """Add a ``[pending_turn]`` intent record to ``document`` in place."""


def clear_pending_turn(document: TOMLDocument) -> None:
    """Remove the ``[pending_turn]`` record from ``document`` in place."""


@contextlib.contextmanager
def pending_turn(
    path: Path, *, operation: str, paths: cabc.Sequence[str]
) -> cabc.Iterator[TOMLDocument]:
    """Bracket a multi-file mutation: load ``state.toml``, write a
    ``[pending_turn]`` record atomically, yield the document for the caller's
    artefact work, then clear the record and write atomically on clean exit.
    On an exception the record is left populated for the next turn to
    reconcile (design §3.4).

    The yielded ``TOMLDocument`` is the *single write source* for the
    clean-exit write: the clear-and-write re-dumps the same document the caller
    mutated in-bracket, never a reloaded fresh copy. A caller that edits state
    *values* on the yielded document (e.g. ``recount`` updating
    ``word_counts``) therefore keeps those edits after a clean exit. This task
    owns only the *producer* side — writing and leaving the record; the §5.4
    rollback path ("leave ``state.toml`` at the prior coherent point") is
    ``reconcile``'s job (task 2.3.2), not this helper's."""
```

The exact signatures may be refined during implementation, but
`write_document_atomically` (temp-in-dir + `Path.replace`), the no-op
round-trip, the clean-exit write-source being the yielded caller-mutated
document, and the `pending_turn` open/leave-on-error/clear-on-success behaviour
are load-bearing and pinned by tests. Re-export the public names from
`novel_ralph_skill/state/__init__.py` and update its `__all__` and the
module-level docstring (which currently says "Writing is task 2.2.1").

## Plan of work

Work proceeds in four atomic, independently committable, gate-passable work
items, each ending in validation. Each is a single logical unit per AGENTS.md
"Atomicity".

### Work item 1 — Add the comment-bearing fixture, scaffold the writer module, and a failing round-trip property (red)

Create `novel_ralph_skill/state/document.py` with `load_document`,
`document_to_state`, and `write_document_atomically` as the first seams (full
docstrings, no behaviour beyond `load_document`/`document_to_state` reads and a
deliberately-incomplete or `NotImplementedError` write). Add
`tests/test_state_document.py` defining a module-level
`COMMENT_BEARING_STATE_TOML` constant: a hand-authored, schema-valid
`state.toml` string carrying **block comments, at least one inline value
comment, deliberate blank-line layout between tables, an inline `by_chapter`
table, and an array-of-tables `[[chapters]]`** (mirroring the §5.1 schema so
`parse_state`/`document_to_state` accepts it). The round-trip **property** test
draws over this fixture (and, as an additional case, the comment-free corpus
trees) and is marked to fail until work item 2 lands.

Docs to read first: design §5.3 and §3.4; ADR-002 (Functional and Technical
requirements); `docs/scripting-standards.md` "Reading / writing files and
atomic updates"; AGENTS.md "Python verification and testing"; developers-guide
"Shared test scaffolding" and "The `working/` fixture corpus".

Skills to load: `python-router` (route to `python-data-shapes` for the
document/State boundary and `python-verification`); after `python-verification`
confirms it, `hypothesis` for the property test.

Tests this item adds:

- A Hypothesis property test (`hypothesis`, per AGENTS.md "property tests … when
  a change introduces an invariant over a range of inputs") asserting the no-op
  round-trip is byte-for-byte stable. The strategy draws over a set of
  **comment-and-layout-bearing** `state.toml` documents —
  `COMMENT_BEARING_ STATE_TOML` plus any small permutations of it (e.g. comment
  text variants, reordered inline-table keys) generated by a Hypothesis
  strategy over a list of hand-authored comment-bearing templates — reading
  each document's bytes and asserting
  `tomlkit.dumps(load_document(p)) == original_bytes`. This is the guard design
  §9 names ("a no-op `recount` preserves formatting and comments" — the §5.3
  round-trip property) and the assertion ADR-002 Functional req 1 requires
  ("including comments and whitespace"). It must constrain comment and
  whitespace preservation, which it can only do over comment-bearing input
  (round-1 review B1).
- An **additional** parametrized case over the comment-free corpus trees:
  across the `coherent_oracle_cases` / `phase_state_tree` factory callables
  (eleven phase states plus the baseline), read each tree's
  `(working_dir / "state.toml").read_text()` and assert the same byte identity.
  This is breadth over the real schema shapes, but it is *not* the carrier of
  the comment guarantee (the corpus has no comments to lose).

Validation: `make all` — the new property test must **fail** here (red),
proving the suite exercises the not-yet-implemented write path. Commit the red
scaffold (tests plus stub module) only if the rest of the gate (`check-fmt`,
`lint`, `typecheck`) is green; mark the failing test `xfail` with a reason
pointing at work item 2 so the gate stays green at commit time, then remove the
`xfail` in work item 2.

### Work item 2 — Implement the lossless round-trip and atomic write (green)

Implement `write_document_atomically`: serialize with `tomlkit.dumps`, write to
a `tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, ...)`, then
`Path.replace` the temp path over the target; on any exception before the
replace, unlink the temp file. Remove the `xfail` from the round-trip property.

Docs to read first: design §5.3, §3.4; `docs/scripting-standards.md` atomic
write pattern and "Operational guidelines" (idempotence); ADR-002 Functional
requirements 1-2.

Skills to load: `python-router` → `python-errors-and-logging` (narrow `except`,
unlink-on-failure cleanup), `python-data-shapes`; `hypothesis` for the property.

Tests this item adds or turns green:

- The round-trip property from work item 1 now passes (green) — both the
  comment-bearing input and the corpus sweep.
- A Hypothesis **property** (not a lone example) asserting the surgical-mutation
  comment-preservation: over the comment-bearing fixture (and a strategy of
  integer values to write into `word_counts.current`), set that value and
  assert the output equals a *string replacement* of the old value's bytes in
  the original — i.e. only the touched value's bytes changed and **every
  comment and blank-line layout survived** (block comment present, the inline
  value comment present, table order and spacing unchanged). This is the "no-op
  `recount` preserves formatting and comments" criterion design §9 names and
  the "a real mutation changes only the targeted values, leaving surrounding
  formatting and comments intact" requirement of ADR-002 Functional requirement
  2, pinned at the locked tomlkit 0.15.0 over comment-bearing input (round-1
  review B2/B3). It must **not** rely on the comment-free corpus, where "the
  comment text is preserved" is vacuously true.
- A unit test for `write_document_atomically` asserting: (a) the live file
  contents equal `tomlkit.dumps(document)` after a successful write; (b) the
  temporary file is created in `path.parent` (asserted via a spy/monkeypatch on
  `tempfile.NamedTemporaryFile` or by listing the directory during the write);
  (c) on a forced failure before `Path.replace` the prior file is unchanged and
  no stray temp file remains (the "untorn on crash" requirement, design §3.4).

Validation: `make all` green.

### Work item 3 — Add `pytest-bdd`, then implement the `[pending_turn]` bracket and interrupted-write recovery

**Dependency step (do this first, as its own atomic commit).** Add `pytest-bdd`
to `[dependency-groups].dev` in `pyproject.toml` (the suite's first behavioural
test needs it; AGENTS.md line 143). Regenerate the lock with
`UV_CACHE_DIR=.uv-cache UV_TOOL_DIR=.uv-tools uv lock`, then re-sync with
`make build` (which runs `uv sync --group dev`). Add a version-pin guard test
`tests/test_pytest_bdd_dependency.py` mirroring
`tests/test_contract_test_deps.py`: assert `pytest_bdd` imports, that its
resolved version equals a `LOCKED_PYTEST_BDD_VERSION` constant set to whatever
`uv lock` resolves (read via `importlib.metadata.version("pytest-bdd")`), and
that `pytest-bdd` is declared in `[dependency-groups].dev` of `pyproject.toml`.
This is the same re-resolution tripwire the existing dependency guards use, so
a silent `uv` re-resolution fails the guard while a deliberate upgrade updates
the pin visibly. Commit this as a discrete "Add pytest-bdd behavioural-test
dependency" change with `make all` green before touching the writer behaviour.
Reconcile with the Tolerances "Dependencies — dev/test" carve-out: this is a
sanctioned AGENTS.md-mandated dev dependency, not the forbidden runtime
addition; do **not** stop-and-escalate here (round-2 review B4).

Place the behavioural test's step module under `tests/steps/` (the directory
`pyproject.toml` line 97 already exempts from `S101`/`PLR` rules) and its
`.feature` file alongside the test module per the project layout. This is the
first `.feature` file and the first `tests/steps/` module in the suite.

Then implement `open_pending_turn`/`clear_pending_turn` (add/remove the
`[pending_turn]` table, populating `operation` and `paths`) and the
`pending_turn` context manager that loads the file, writes the record
atomically *before* yielding, and on clean exit clears the record and writes
atomically; on an exception it re-raises and leaves the populated record on
disk. The keys (`operation`, `paths`) must match `PendingTurn` in `schema.py` so
`parse_state` reads the record back. The clean-exit clear-and-write re-dumps
the **yielded, caller-mutated** document — the single write source — so an
in-bracket value edit survives a clean exit (round-1 review A1). This task owns
only the producer side; the §5.4 rollback recovery is `reconcile`'s (task
2.3.2), and the plan signposts that boundary rather than implementing it here
(A2).

Docs to read first: design §3.4 (the `[pending_turn]` paragraph), §5.1 (the
`[pending_turn]` schema bullet), §5.4 (how `check`/`reconcile` consume it), §10
("Torn multi-file turn"); `schema.py` `PendingTurn`.

Skills to load: `python-router` → `python-abstractions` (the context-manager
form and its clean-exit-versus-error contract), `python-errors-and-logging`,
`python-testing` (the `pytest-bdd` scenario/step/`.feature` wiring and fixture
scopes); after `python-verification` confirms it, `hypothesis` for the
clear-restores property.

Tests this item adds:

- The `pytest-bdd` version-pin guard `tests/test_pytest_bdd_dependency.py`
  described in the dependency step above (a re-resolution tripwire, not a
  presence-only check).
- A behavioural test using `pytest-bdd` (now installed by the dependency step;
  per AGENTS.md line 143 and design §9 "behavioural tests cover the
  harness-facing flows") of the torn-turn scenario, with a `.feature` file and
  a step module under `tests/steps/`: Given a settled corpus `state.toml`, When
  a `pending_turn` bracket raises in the artefact step, Then `state.toml` holds
  a populated `[pending_turn]` whose `operation` and `paths` are the declared
  ones, and the prior tables are otherwise intact (the design §3.4 "died
  mid-write" signature). This is the success criterion the roadmap names: "a
  write interrupted before completion leaves a populated `[pending_turn]`
  record for the next turn to reconcile."
- A property/example test asserting the *clear-restores* contract: opening then
  cleanly clearing `[pending_turn]` on a settled document yields a document
  that re-parses (`parse_state`/`document_to_state`) to a `State` equal to the
  original and carries no `[pending_turn]` (parsed-equality, not byte-for-byte
  — see Risk "pending_turn whitespace").
- A unit test asserting `open_pending_turn` followed by `parse_state` over the
  document's plain mapping produces a `State` whose `pending_turn` is a
  `PendingTurn(operation=..., paths=(...))` matching the inputs (the schema
  round-trips through the writer).
- A unit/behavioural test pinning the A1 contract: open the bracket on a settled
  `state.toml`, mutate a state *value* on the yielded document inside the
  bracket (e.g. set `word_counts.current` to a new total), exit cleanly, then
  re-read the file and assert the value edit survived **and** `[pending_turn]`
  is cleared. This proves the clean-exit write re-dumps the caller-mutated
  document, not a reloaded copy (round-1 review A1).
- CLI/error-path coverage is **not** in scope (no CLI here); the exit-code
  contract is exercised by the mutator subcommands in 2.2.2/2.3.x. The §5.4
  rollback path is `reconcile`'s (task 2.3.2) and is out of scope here (A2).

Validation: `make all` green.

### Work item 4 — Export the surface, document it, and run the full gate

Re-export the public names from `novel_ralph_skill/state/__init__.py`
(`__all__` plus the import block) and correct the module docstring line that
currently says writing is "task 2.2.1" (now delivered). Add a short subsection
to `docs/developers-guide.md` under "State and on-disk layout" describing the
`document.py` writer — the lossless round-trip, the atomic discipline, and the
`pending_turn` bracket — so the later mutator tasks find the seam. Cross-check
that the state-layout direct-edit guard
(`tests/test_state_layout_reference.py`) still passes unchanged (this task adds
a sanctioned writer module; it must not introduce a hand-edit *recipe* in
`state-layout.md`).

Docs to read first: developers-guide "State and on-disk layout" and "The
state-layout direct-edit guard"; AGENTS.md "Documentation maintenance";
`docs/documentation-style-guide.md`.

Skills to load: `en-gb-oxendict` for the prose; `python-router` if the export
edit touches typing.

Tests this item adds or updates: none new beyond an import-surface assertion if
one is warranted (e.g. asserting `document.py`'s public names are re-exported);
the behavioural and property suites from items 1-3 carry the behaviour.

Validation: `make all`; and because Markdown changed, `make markdownlint` and
`make nixie` (no Mermaid added, but run `nixie` per the standing rule for
Markdown changes). Paragraphs wrapped at 80 columns, code blocks at 120
(AGENTS.md "Markdown guidance").

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-2-1`.

1. Confirm the starting branch and a clean tree:

   ```bash
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-2-1 \
     branch --show-current
   # expect: roadmap-2-2-1
   ```

2. Work item 1: create `novel_ralph_skill/state/document.py` and
   `tests/test_state_document.py` — the latter defining the
   `COMMENT_BEARING_STATE_TOML` fixture and the round-trip property over it
   (red scaffold, failing property `xfail`ed with a reason). Run the gate:

   ```bash
   make all
   ```

   Expect the suite to pass with the round-trip test reported `xfailed`.

3. Work item 2: implement the round-trip and atomic write; remove the `xfail`.

   ```bash
   make all
   ```

   Expect all tests passed, including the round-trip property and the
   atomic-write unit tests.

4. Work item 3: first add `pytest-bdd` as a dev dependency and regenerate the
   lock, then implement the `[pending_turn]` bracket and add the behavioural
   and clear-restores tests.

   ```bash
   # dependency step (its own commit)
   UV_CACHE_DIR=.uv-cache UV_TOOL_DIR=.uv-tools uv add --dev pytest-bdd
   # `uv add --dev` edits pyproject.toml's [dependency-groups].dev and updates
   # uv.lock in one step; alternatively edit pyproject.toml by hand then run
   # `UV_CACHE_DIR=.uv-cache UV_TOOL_DIR=.uv-tools uv lock`.
   make all   # version-pin guard green; commit the dependency addition
   # then the behaviour:
   make all
   ```

   Expect the version-pin guard, the torn-turn behavioural scenario, and the
   clear-restores property to pass.

5. Work item 4: export and document. Because Markdown changed:

   ```bash
   make all
   make markdownlint
   make nixie
   ```

   Expect all three green.

Commit after each work item with a clear, imperative, en-GB message (e.g. "Add
lossless tomlkit round-trip and atomic state writer"). Commit only when the
gate is green (AGENTS.md "Committing"). Use the `commit-message` skill.

## Validation and acceptance

Acceptance is behaviour a human can verify:

- **Round-trip property over comment-bearing input.** `make test` passes and
  `tests/test_state_document.py` includes a Hypothesis property that fails
  before work item 2's implementation (it is `xfail` in the red scaffold) and
  passes after: reading a hand-authored comment-and-layout-bearing `state.toml`
  (block comments, inline value comments, blank-line layout, an inline table,
  and an array-of-tables), writing it back with no edit, and comparing bytes
  shows them identical — and a surgical `word_counts.current` mutation rewrites
  only that value while every comment survives. The comment-free corpus sweep
  runs as an additional case. This is the §5.3 round-trip property design §9
  names and ADR-002 Functional req 1's "including comments and whitespace"
  guarantee, verified at the locked tomlkit 0.15.0 (round-1 review B1/B2/B3).
- **Atomic write.** A unit test shows the temp file is created in the target
  directory and that a forced failure before `Path.replace` leaves the prior
  `state.toml` byte-for-byte unchanged with no stray temp file (design §3.4).
- **`[pending_turn]` recovery.** A `pytest-bdd` scenario (with a `.feature` file
  and a step module under `tests/steps/`, made runnable by the work-item-3
  dependency step that adds `pytest-bdd` to `[dependency-groups].dev`) shows an
  interrupted multi-file turn leaves a populated `[pending_turn]` naming the
  operation and paths, with the prior tables intact (roadmap 2.2.1 success
  criterion; design §3.4, §10; AGENTS.md line 143). A version-pin guard
  (`tests/test_pytest_bdd_dependency.py`) confirms the locked `pytest-bdd`
  version, mirroring the existing dependency tripwires.

Quality criteria ("done" means):

- Tests: `make test` passes (`pytest -v -n $(PYTEST_XDIST_WORKERS)`), including
  the new property, behavioural, and unit tests.
- Lint/format/type: `make check-fmt`, `make lint` (Ruff + 100% `interrogate`
  docstring coverage + Pylint), and `make typecheck` (`ty`) all pass.
- Audit: `make audit` (`pip-audit`) passes. No new *runtime* dependency is added
  (the `[project].dependencies` surface is unchanged); the one new *dev/test*
  dependency, `pytest-bdd`, is a behavioural-test tool under
  `[dependency-groups].dev`, and `pip-audit` covers it.
- Markdown: `make markdownlint` and `make nixie` pass for the developers-guide
  and execplan edits.
- Aggregate: `make all` is green.

Quality method: run `make all` (and `make markdownlint`/`make nixie` for the
Markdown changes) locally before each commit; the CI workflow runs the same
gates.

## Idempotence and recovery

Every step is re-runnable. `make all` is idempotent. The atomic write is
idempotent by construction: re-running a no-op write produces the same bytes.
If a work item's gate fails, fix forward and re-run `make all`; nothing in this
task mutates state outside `tmp_path` during tests or the new module under
`novel_ralph_skill/`. No destructive operation is involved; there is no
rollback to script beyond `git restore` of the in-progress edit.

## Artifacts and notes

Empirical round-trip probe, **re-run under the `uv`-resolved tomlkit 0.15.0**
(`uv run python` against `uv.lock` lines 667-672; `tomlkit.__version__` reported
`0.15.0`), over a hand-authored comment-and-layout-bearing `state.toml` with
block comments, an inline value comment (`current = 1234  # running total`),
blank-line layout, an inline `by_chapter` table, and an array-of-tables
`[[chapters]]`:

```plaintext
=== tomlkit 0.15.0 ===
NOOP_BYTE_IDENTICAL: True
VALUE_MUTATION_SURGICAL: True
  running-total comment kept: True
  block comment kept: True
```

`[pending_turn]` add-then-remove whitespace artefact, **also at 0.15.0**
(motivates the parsed-equality guarantee for the clear-restores property, not
byte-for-byte):

```plaintext
HAS_PT: True
REMOVED_EQ_SRC: False   # 507 vs 506 bytes — a residual blank line
REPARSE_EQ_KEYS: True   # the cleared document re-parses to the same tables
```

These supersede the earlier 0.14.0 ambient probe: the mechanism is verified at
the shipped, locked version, over comment-bearing input, so no cross-version
"behaves identically" assertion is relied upon (round-1 review B3). The
verification of record is the comment-bearing property test running at 0.15.0
under `make test`; the probe above is corroborating evidence at the same
version.

Official tomlkit docs confirming the same mechanism (the public
`readthedocs.io/en/latest/quickstart/` build currently renders the 0.13.x docs
page text, but the API it documents is unchanged through the 0.15.0 line, and
the locked 0.15.0 wheel is verified empirically above):

- `https://tomlkit.readthedocs.io/en/latest/quickstart/` — "fast and
  style-preserving parser", `assert dumps(doc) == content` (no-op round-trip),
  and the modify example showing `doc["table"]["baz"] = 13` preserves the
  `# String` comment.

## Revision note

Round-3 revision (2026-06-22): resolved round-2 review blocking defect B4 — the
mandated behavioural test depended on `pytest-bdd`, which is not installed and
which the plan neither added nor reconciled with its own dependency Tolerance.

What changed:

- The dependency Tolerance was split into "Dependencies — runtime" (forbidden
  beyond `cyclopts`/`tomlkit`) and "Dependencies — dev/test" (a new dev/test
  dependency is permitted only when AGENTS.md mandates it; `pytest-bdd`
  qualifies under AGENTS.md line 143). The Scope Tolerance grew from six to
  ~ten files to absorb the new guard/feature/step files.
- Work item 3 now opens with an explicit, separately-committed dependency step:
  add `pytest-bdd` to `[dependency-groups].dev`, regenerate `uv.lock`, add a
  version-pin guard `tests/test_pytest_bdd_dependency.py` mirroring
  `tests/test_contract_test_deps.py`, and place the behavioural test's
  `.feature` file and step module under `tests/steps/` (already exempted by
  `pyproject.toml` line 97).
- The Interfaces, Progress, Decision log, Concrete steps, and Validation
  sections were updated to name the `pytest-bdd` addition, its guard, and the
  `tests/steps/` layout, and the audit/quality criteria now distinguish the
  unchanged runtime surface from the one new dev/test dependency.

Why: AGENTS.md line 143 mandates `pytest-bdd` for behavioural tests, so adding
it as the suite's first behavioural-test dependency is sanctioned dev tooling,
not a forbidden runtime dependency — but it had to be a named work-item step
with the Tolerance reconciled, so the implementer does not stop-and-escalate on
a routine addition (round-2 pre-mortem).

Effect on remaining work: work item 3 gains a leading dependency commit; the
total file/line budget rises accordingly. No other work item changes. The plan
remains DRAFT pending re-review.
