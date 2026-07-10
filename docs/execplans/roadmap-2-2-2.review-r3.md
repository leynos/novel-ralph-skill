# Logisphere design review — roadmap 2.2.2 ExecPlan, round 3

Adversarial pre-implementation review of `docs/execplans/roadmap-2-2-2.md`
(`init`, `set-cursor`, `advance-phase`). Verdict: **Proceed**. Every
load-bearing claim was independently re-verified against the worktree source
and the locked libraries; the two round-2 blocking points (BR2-1, BR2-2) are
genuinely resolved.

## What was independently verified (not taken on the planner's word)

- **`runner.run` catch arms (BR2-1 ground truth).** Read
  `novel_ralph_skill/contract/runner.py`: exactly two `except` arms —
  `CycloptsError` → exit 2, `StateInputError` → exit 3 — and no broad
  `except Exception`. Any other exception exits 1. The plan's whole
  `_state_view_or_state_error` argument rests on this, and it holds.
- **BR2-1 structurally-incomplete case.**
  `tomlkit.parse("schema_version = 1\n")`
  yields a `TOMLDocument` that `load_document` accepts, but `document_to_state`
  raises `NonExistentKey` (a `KeyError`) — confirmed live. A bad phase string
  raises `ValueError` from `Phase(...)`. So the typed-view derivation can fail
  on a TOML-valid file and **must** be wrapped at its call site; subsumption by
  `STATE_INPUT_ERRORS` alone is insufficient. The plan's two-helper split
  (`_load_document_or_state_error` + `_state_view_or_state_error`) is the
  correct fix and the planned `"schema_version = 1\n"` contract test pins it.
- **Fault subclass facts.**
  `issubclass(tomlkit.exceptions.ParseError, ValueError)`
  and `issubclass(NonExistentKey, KeyError)` both `True`; unparseable input
  raises `UnexpectedCharError` (a `ValueError`), missing file raises
  `FileNotFoundError` (an `OSError`). `STATE_INPUT_ERRORS` subsumes all of
  them. Confirmed live.
- **D6 into-`drafting` success tree.** Built the exact `WorkingTreeSpec`
  (`phase_current="chapter-planning"`, `phase_completed=PHASE_ORDER[:7]`, three
  zero-draft chapters, `current_chapter=0`); prior `validate_state` empty, and
  after appending `chapter-planning` + setting `current="drafting"` the
  proposed state is **still** coherent (empty verdict). Confirmed live.
- **B3 out-of-order refusal.** `INCOHERENT_VARIANTS["completed-prefix-gap"]` is
  a
  `drafting`-phase tree with `completed=("premise","characters")`; prior
  verdict is `["completed-prefix"]`, and advancing keeps it
  `completed-prefix`-violated, so the advance is refused. Confirmed live. The
  "advance cannot skip; out-of-order is realized solely as the prior-coherence
  guard" reasoning matches `validate.py:_check_completed_prefix`.
- **Cyclopts 4.18.0 kebab mapping.** Registered `set_cursor`/`advance_phase` on
  a
  real app; command names resolve to `set-cursor`/`advance-phase` and
  keyword-only params map to `--chapter` etc. Confirmed live, not from memory.
- **BR2-2 directory skeleton.** `skill/novel-ralph/references/state-layout.md`
  "Initialization" step 1 is
  `mkdir -p working/{characters,world,reader,plan,manuscript,reviews}`, step 3
  creates an empty `log.md`, default `target_word_count` 80000,
  `phase.current = "premise"`. "First turn: working/ does not exist" + "Never
  delete files in `working/`. State is precious." together ground the
  create-not-overwrite (exit 3) decision. All confirmed against the real file.
- **Validator / parser strict boundary, cursor coherence, fixtures, make
  targets,
  pytest-timeout (default 30s) + pytest-xdist, the direct-edit guard test, and
  the developers-guide anchors** the plan cites all exist as described.

## Advisory (non-blocking)

- **A-R3-1 — `[[chapters]]` wording is a construction trap.** Work item 2 and
  the
  Interfaces section describe the required shape as "`[[chapters]]`: an empty
  array". `[[chapters]]` is array-of-tables syntax and has **no** empty form;
  the buildable shape `parse_state` reads is a top-level `chapters = []` key
  (`doc.add("chapters", [])`), and — verified live — it must be added
  **before** any `[table]` header or `tomlkit`/TOML will nest it under the
  preceding table (e.g. it parses as `[word_counts].chapters`, and
  `parse_state` then raises `NonExistentKey` on `raw["chapters"]`). The corpus
  `_build_state_document` is the correct reference. Recommend the plan say "a
  top-level `chapters = []` array, emitted before the first table" rather than
  `[[chapters]]`. Non-blocking: the work-item-2 "parse_state succeeds before
  any field assertion" test will catch a mis-placed key immediately, and the
  Verified Facts already cite `raw["chapters"]` and the corpus builder
  correctly.

- **A-R3-2 — `state-layout.md` path.** The plan refers to the source as
  bare "state-layout.md"; it actually lives at
  `skill/novel-ralph/references/state-layout.md`, not `docs/`. The content is
  correct and authoritative; only the citation path is implicit. Implementer
  should read it there.

## Panel notes

- **Pandalump (structure):** boundaries hold — mutators write only through
  `write_document_atomically`, validate the proposed state via a read-only
  `document_to_state` view, and never re-serialize the lossy `State`. The
  document-is-write-source / `State`-is-validation-view split is preserved.
- **Telefono (contracts):** no public signature changes; two module-private
  helpers added; the exit-3 refusal contract is closed on every path (load,
  typed-view, validator, terminal, empty-manifest). The §3.2 1-vs-3 distinction
  is the load-bearing contract and it is now leak-free.
- **Doggylump (failure modes):** refusal-writes-nothing is structural (write
  only
  after validation), byte-for-byte assertions pin it, and the 3-not-1
  regression is guarded by an explicit `ExitCode.STATE_ERROR` assertion plus a
  subclass-fact unit test against library drift. Pre-mortem ("init clobbers a
  live project") is designed out by the create-not-overwrite refusal.
- **Buzzy Bee (scaling):** single-file atomic writes, no `[pending_turn]`
  bracket
  needed (correctly scoped to multi-file turns); no cost concern at novel scale.
- **Dinolump (viability):** matches the 2.2.1 discipline the team already built;
  developers-guide subsection documents the pattern for `recount`/`reconcile`.
- **Wafflecat (alternatives):** the strongest alternative — a single
  `_load_state_view_or_error` that loads-and-derives in one wrapped call — was
  implicitly rejected for good reason: the mutators need the live
  `TOMLDocument` (write source) AND the typed `State` (validation view) as
  separate objects, so the two-helper split is the right factoring, not
  over-engineering.

## Verdict

**Proceed.** No blocking defects. Work items are atomic, ordered (red →
per-command green → docs/snapshots), independently committable, and each ends
in a named validation. Refusal exit-3 channel is fully closed and pinned.
Address the two advisories opportunistically during implementation.
