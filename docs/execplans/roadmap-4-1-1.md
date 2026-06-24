# Implement `novel-compile` ordered by the zero-padded chapter index

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DELIVERED

## Purpose / big picture

The harness regenerates the whole-novel manuscript by concatenating the chapter
drafts. Today that is hand-rolled: the field report records an agent gluing
`working/manuscript/chapter-NN/draft.md` files together with a directory glob,
so the join order depends on the filesystem listing and the separators drift
turn to turn (design `docs/novel-ralph-harness-design.md` §4.3, §8, §10). This
task delivers `novel-compile` as a deterministic **mutator**: it concatenates
the chapter drafts in zero-padded chapter-index order with one fixed separator
and writes `working/manuscript/compiled.md` atomically, so identical drafts and
manifest always produce a byte-identical `compiled.md` regardless of directory
listing order. No outline prose is parsed; ordering *is* the zero-padded chapter
index, validated against the manifest (design §4.3 resolves assumption A5).

This task is the **write path only**. The read-only `--check` divergence checker
and the shared compile-and-hash routine are roadmap tasks 4.1.2 and 3.1.2, which
are explicitly out of scope here (see Decision Log D-SCOPE). 4.1.1 requires only
"phase 2", which is delivered; it must not take a dependency on the not-yet-built
hash routine.

After this change a user can run, from a project's process directory:

```console
$ novel-compile
{"command": "novel-compile", "schema_version": 1, "ok": true,
 "working_dir": "working",
 "result": {"compiled": "working/manuscript/compiled.md",
            "chapters": 3, "bytes": 412},
 "messages": ["compiled 3 chapters into working/manuscript/compiled.md"]}
```

and observe `working/manuscript/compiled.md` rewritten to the ordered
concatenation of `chapter-01/draft.md`, `chapter-02/draft.md`, … joined by the
fixed `DRAFT_SEPARATOR`. Two consecutive runs over unchanged drafts produce a
byte-for-byte identical `compiled.md` (determinism/idempotence). On a tree whose
chapter manifest (`[chapters]` in `state.toml`) is absent or empty, the command
refuses with exit `3` and writes nothing — there is no authoritative ordering to
follow (design §10 "Chapter manifest missing or non-bijective during compile").

The behaviour is observable through a new behavioural scenario
(`tests/features/compile.feature`) and a machine-mode envelope snapshot, both
described under "Validation and acceptance".

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **Ordering is the zero-padded chapter index, taken from the manifest.** The
  compile order is the ascending `[chapters]` manifest chapter number, which
  drives the `chapter-{number:02d}` directory name (design §4.3 lines 357-369;
  §5.1 lines 418-424). No directory glob decides order, and no outline prose is
  read. This is the disk-outline bijection that closes the ambiguous-ordering
  failure mode; `novel-state check` (delivered) already asserts the manifest is
  in bijection with the on-disk directories (§5.2), so the manifest order and
  the directory index agree before any compile runs.
- **One fixed separator, reused from the existing production model.** The
  ordered draft bodies are joined by `novel_ralph_skill.state.compile_model`'s
  `DRAFT_SEPARATOR` (`"\n\n"`) via its `concatenate_drafts` function — the
  single production source of truth the §5.4 disk-evidence detector already
  uses (`novel_ralph_skill/state/disk_evidence.py:179-196`;
  `novel_ralph_skill/state/compile_model.py:26-53`; design §4.3 "consistent
  separators", §9). The write path **must** reuse this routine rather than
  inventing a second join rule, or `novel-compile` and the
  `compiled-matches-drafts` invariant would disagree about what a coherent
  `compiled.md` is. The corpus's `CORPUS_SEPARATOR`
  (`tests/working_corpus/_specs.py:38`) is the independent test twin, pinned
  equal by `tests/test_disk_evidence.py`.
- **Draft-body read rule matches the disk-evidence detector exactly.** Each
  manifest chapter's body is `(chapter_dir / "draft.md").read_text("utf-8")`,
  and an **absent** `draft.md` contributes the empty string — byte-for-byte the
  `_present_draft_bodies` rule in
  `novel_ralph_skill/state/disk_evidence.py:164-176`. `novel-compile` must read
  bodies the same way so its output equals what
  `_check_compiled_matches_drafts` expects (otherwise a freshly compiled tree
  would immediately fail `novel-state check`). Reuse that helper rather than
  re-deriving the read.
- **Exit `3` when the manifest is absent or empty; write nothing.** An empty or
  missing `[chapters]` manifest has no authoritative ordering, so `novel-compile`
  raises `StateInputError` (exit `3`, the state/input channel — ADR-003; design
  §3.2, §10 lines 811-815) and writes no `compiled.md`. This is distinct from the
  benign `1` the loop continues on: a missing manifest means the agent must
  complete chapter planning first. A missing/unparseable `state.toml`, an absent
  `working/` directory, or an unreadable/undecodable `draft.md` is likewise exit
  `3` (the established `STATE_INPUT_ERRORS` boundary in
  `novel_ralph_skill/commands/novel_state.py:116-122`).
- **Atomic write via temp-file-plus-`Path.replace`.** `compiled.md` is written
  to a temporary file in `working/manuscript/` followed by `Path.replace`, which
  is atomic on POSIX, so a crash mid-write leaves the prior `compiled.md` intact
  (design §3.4 lines 245-251; `docs/scripting-standards.md`). The existing
  `write_document_atomically` (`novel_ralph_skill/state/document.py:114-151`) is
  TOML-specific (`tomlkit.dumps`); this task adds a *text* twin that writes a
  pre-rendered string with the same temp-file discipline (Decision Log D-WRITER).
- **Success `result` is write-shaped, never a checker's read shape.** A mutator's
  success `result` names *what it changed*; the `violations` key is reserved for
  checkers alone (design §3.3 lines 166-179;
  `docs/developers-guide.md:202-208`). `novel-compile`'s write success returns
  the written path, chapter count, and byte length — not `violations`, and not
  `compile_consistent` (that is `novel-done`'s 3.1.1 shape).
- **`novel-compile` is a single default command, not a subcommand multiplexer.**
  Unlike `novel-state`, `novel-compile` maps 1:1 onto one deterministic
  operation (design §4 lines 265-273; ADR-005). For 4.1.1 the Cyclopts app
  exposes a single default callback (the write). The `--check` flag is added by
  4.1.2 and is out of scope here (Decision Log D-SCOPE).
- **The command shells out to nothing — no cuprum surface is added.**
  `novel-compile` is pure Python file I/O over `pathlib` plus the in-package
  `concatenate_drafts`; design §4 lines 267-270 record that no v1 command
  invokes an external process for its core logic, so the cuprum catalogue
  boundary is not exercised (Decision Log D-CUPRUM). Adding a cuprum/subprocess
  execution path here is out of scope and a tolerance breach.
- **`[pending_turn]` bracket: single-file write, so no bracket.** `novel-compile`
  writes exactly one file (`compiled.md`), already atomic via `Path.replace`,
  exactly like `recount`/`set-cursor`/`advance-phase`. It opens **no**
  `[pending_turn]` intent record (design §3.4 lines 253-263 — the bracket is for
  *genuinely multi-file* turns). Note: `docs/developers-guide.md:205-208` and
  `:596` currently list `novel-compile` among the `[pending_turn]`-bracketed
  multi-file writers; this is a documentation defect this task corrects, exactly
  as task 2.3.1 corrected the parallel `recount` mis-listing (Decision Log
  D-PT; Surprises).
- **No file in `working/` is ever deleted.** `novel-compile` only writes
  `compiled.md`; it never removes a draft, a `done.flag`, or any artefact
  (design §5.4 "No file in `working/` is ever deleted").
- **en-GB Oxford spelling** (`-ize`/`-yse`/`-our`) in all prose, comments, and
  commit messages (AGENTS.md; the en-gb-oxendict convention), with the standard
  carve-out for external API names.
- **400-line module cap** per file (AGENTS.md "Keep file size manageable").

## Tolerances (exception triggers)

Stop and escalate (do not work around) when any threshold is reached:

- **Scope:** if the production change (the new command module plus a text-writer
  helper) exceeds ~220 net new lines, or touches more than 5 non-test files,
  stop and escalate.
- **Interface:** if `CommandOutcome`/`StateInputError`/`ExitCode`, the
  `RunContext`/`run` wrapper, or any existing public signature must change to add
  `novel-compile`, stop and escalate. (Adding a new command module and wiring the
  `novel_compile` entry point in `stub.py` is in scope; mutating existing public
  signatures is not.)
- **Dependencies:** if any new external dependency (including any cuprum
  execution path or subprocess call) appears necessary, stop and escalate — the
  Constraints forbid it.
- **Separator divergence:** if the write path cannot reuse
  `compile_model.concatenate_drafts`/`DRAFT_SEPARATOR` and the disk-evidence
  `_present_draft_bodies` read rule and still produce output that
  `_check_compiled_matches_drafts` accepts for every coherent corpus tree, stop
  and escalate rather than introducing a second join or read rule.
- **Scope creep into 4.1.2/3.1.2:** if implementing 4.1.1 appears to require the
  `--check` flag or a compile-and-hash routine, stop and escalate — those are
  separate roadmap tasks (D-SCOPE).
- **Iterations:** if `make all` still fails after 3 fix attempts on a single
  work item, stop and escalate.
- **Ambiguity:** if a manifest-vs-disk interaction makes the "empty manifest →
  exit 3" boundary (D-EMPTY) materially change behaviour beyond what its test
  pins, stop and present options.

## Risks

- Risk: `novel-compile`'s output diverges from what the `compiled-matches-drafts`
  disk-evidence invariant expects (a different separator, a different read rule,
  or a different order), so a freshly compiled tree immediately fails
  `novel-state check`. Severity: high Likelihood: low Mitigation: reuse
  `compile_model.concatenate_drafts` and the disk-evidence `_present_draft_bodies`
  read rule directly (Constraints), and pin the round-trip with a test that
  `novel-compile` then `check_disk_evidence` reports no `compiled-matches-drafts`
  violation over every coherent corpus tree (Work item 2).

- Risk: a non-deterministic write (dict/set iteration order over chapters, or a
  glob-derived order) breaks the byte-identical success criterion. Severity:
  medium Likelihood: low Mitigation: order strictly by the manifest's ascending
  chapter number (`sorted(state.chapters, key=lambda c: c.number)`), never by a
  directory glob, and assert byte-for-byte stability of a second run in both a
  unit test and the BDD scenario (Work items 2 and 3).

- Risk: an absent vs. empty `[chapters]` manifest is handled inconsistently, so
  a legitimately empty manifest writes an empty/garbage `compiled.md` instead of
  refusing. Severity: medium Likelihood: medium Mitigation: the typed `State`
  always carries `state.chapters` (possibly an empty tuple); treat
  `len(state.chapters) == 0` as the exit-`3` refusal (D-EMPTY), and test the
  empty-manifest tree explicitly (Work item 2).

- Risk: a `draft.md` that is not valid UTF-8 (or otherwise unreadable —
  permission denied, a directory where a file is expected) raises an exception
  that, if not routed to the exit-`3` channel, escapes as exit `1`. Severity:
  medium Likelihood: low Mitigation: the body-read helper lets every read fault
  other than `FileNotFoundError` propagate (an absent draft is the empty string,
  per the disk-evidence rule); the command body wraps the read in
  `except STATE_INPUT_ERRORS … raise StateInputError … from exc`, mirroring
  `_recount.py:_recount_or_state_error`. Tested with an undecodable draft (Work
  item 2).

- Risk: the `manuscript/` directory does not yet exist when the write runs (a
  partially-bootstrapped tree). Severity: low Likelihood: low Mitigation: `init`
  creates `working/manuscript/` (`novel_state.py:68-75`), and the manifest-driven
  read already requires chapter directories to exist; the atomic writer's
  `path.parent` is `working/manuscript/`. If `manuscript/` is absent the
  temp-file creation raises `FileNotFoundError`, an `OSError` member of
  `STATE_INPUT_ERRORS`, routed to exit `3`. A unit test covers the absent-tree
  refusal.

## Progress

- [x] Work item 1 — Add the shared atomic text writer beside the TOML writer.
      Delivered: `write_text_atomically(text, path)` in
      `novel_ralph_skill/state/document.py`, with `write_document_atomically`
      refactored to delegate to it (one temp-file dance; D-WRITER), re-exported
      from the `state` package. Byte-exact/overwrite/leak-free tests live in a
      new `tests/test_state_text_writer.py` (the writer cases would have pushed
      `tests/test_state_document.py` past the AGENTS.md 400-line cap, so they got
      their own module — see Surprises). `make all` green.
- [x] Work item 2 — Implement the `novel-compile` write body with unit/property
      tests. Delivered: `compile_manuscript()` and `build_app()` in
      `novel_ralph_skill/commands/_compile.py`. The draft-body read rule was
      *promoted* (not wrapped): `disk_evidence._present_draft_bodies` is now the
      re-exported `compile_model.present_draft_bodies`, so the write path and the
      `compiled-matches-drafts` detector are literally the same function (D-READ).
      `tests/test_compile_unit.py` carries the unit, write-shaped-result,
      idempotence, round-trip-oracle, manifest-ordering, absent-draft, and
      exit-`3` refusal cases (empty manifest, missing `state.toml`, undecodable
      draft, absent `manuscript/`) plus the Hypothesis determinism property.
      Red-before-green confirmed by joining with `"\n"` (the equality and
      property cases went red). `make all` green.
- [x] Work item 3 — Wire the `novel_compile` entry point, add the BDD scenario,
      snapshot, e2e reachability, and update the guides. Delivered: `stub.py`'s
      `novel_compile()` now drives the real app via `run`; `tests/test_compile_e2e.py`
      (entry-point reachability, success + empty-manifest exit-`3`),
      `tests/features/compile.feature` + `tests/steps/compile_steps.py` +
      `tests/test_compile_bdd.py` (regeneration + idempotence, empty-manifest
      refusal), and `tests/test_compile_snapshots.py` (success-envelope snapshot,
      paired with semantic assertions). `novel-compile` was promoted to a real
      command in the two stub/e2e gates that previously asserted it exits `2`
      (`tests/test_command_stubs.py`, `tests/test_console_scripts_e2e.py` — both
      `_REAL_COMMANDS` sets), so they now expect its real contract; this was a
      required wiring update the plan implied (see Surprises). Both guides
      corrected: `docs/users-guide.md` documents `novel-compile` as a delivered
      deterministic mutator and removes it from the stub list;
      `docs/developers-guide.md` corrects the `[pending_turn]` mis-listings
      (single-file, no bracket; D-PT) and the compile-and-hash sentence (the
      write reuses `concatenate_drafts`/`present_draft_bodies`; `--check`/hash is
      4.1.2/3.1.2). `make all`, `make markdownlint`, and `make nixie` green.

## Surprises & discoveries

- Observation: the compile join rule `novel-compile` needs already exists in
  production, not only in design prose. Evidence:
  `novel_ralph_skill/state/compile_model.py:30,33-53` defines `DRAFT_SEPARATOR`
  and `concatenate_drafts`, and its module docstring (lines 1-17) states it is
  "the production twin … the full compile-and-hash command is roadmap task
  4.1.1's", and that the disk-evidence detector reuses it. Impact: 4.1.1 has no
  separator fork to resolve — it reuses the one production constant, and the
  `compiled-matches-drafts` invariant becomes a ready oracle for the round-trip.

- Observation: `docs/developers-guide.md` lists `novel-compile` among the
  `[pending_turn]`-bracketed multi-file mutators, but `novel-compile` writes a
  single file. Evidence: design §4.3 lines 350-355 name only `compiled.md` as the
  output; §3.4 lines 253-263 reserve the bracket for "a turn that touches several
  files". `docs/developers-guide.md:205-208` and `:596` bracket `novel-compile`
  with `reconcile`. Impact: `novel-compile` follows the single-file
  `Path.replace` pattern (no bracket), exactly the correction task 2.3.1 applied
  to `recount` (`docs/execplans/roadmap-2-3-1.md` Decision Log D-PT). Work
  item 3 corrects the guide; the design itself is not edited (D-PT-DESIGN).

- Observation (Work item 3): making `novel-compile` real required updating two
  gates that previously hard-asserted it exits `2` as a stub —
  `tests/test_command_stubs.py::test_entry_point_callable_exits_two` and
  `tests/test_console_scripts_e2e.py`'s install loop. Both key off a
  `_REAL_COMMANDS` exclusion set, so adding `novel-compile` (alongside
  `novel-state` and `desloppify`) removed it from the still-stubbed
  parametrization. Evidence: the install-and-exit-two test failed with the real
  command resolving `./working/` and exiting `3` rather than the stub's `2`.
  Impact: behaviour is now proven by `tests/test_compile_e2e.py`; the wheel test
  stays scoped to the two genuinely-stubbed scripts (`novel-done`, `wordcount`).
  This mirrors how `novel-state` (2.1.2) and `desloppify` (5.1.2) were promoted
  out of those same exclusion sets.

- Observation (Work item 1): the writer tests could not live in
  `tests/test_state_document.py` — appending them pushed that module to 439 lines,
  breaching Pylint's `C0302` 400-line cap (AGENTS.md "Keep file size
  manageable"). Impact: the four `write_text_atomically` byte-level cases land in
  a new sibling module `tests/test_state_text_writer.py`, mirroring how
  `_recount.py`/`_desloppify.py` sit beside the mutator module for the same
  reason. The behaviour and coverage are unchanged; only the file boundary moved.

## Decision log

- Decision (D-READ): the draft-body read rule is **promoted**, not wrapped. The
  former `disk_evidence._present_draft_bodies` is moved to
  `novel_ralph_skill/state/compile_model.py` as the public, re-exported
  `present_draft_bodies(state, working_dir)`; `disk_evidence` imports it and the
  `state` package re-exports it. Rationale: the plan's Work item 2 step 1 prefers
  reuse so the compile read rule and the `compiled-matches-drafts` read rule are
  *literally the same function* (Constraints "Draft-body read rule matches the
  disk-evidence detector exactly"). The promotion diff is small — a function
  move, one import line in `disk_evidence`, and two `__init__` lines — and well
  within tolerance, so the thin-wrapper fallback was not needed. `compile_model`
  is the natural home: it already owns `concatenate_drafts`/`DRAFT_SEPARATOR`, so
  the read-and-join compile rules are co-located and `disk_evidence` already
  imports from it (no new import cycle). Date/Author: 2026-06-24, implementing
  agent.

- Decision (D-SCOPE): 4.1.1 implements the **write path only**; the `--check`
  read-only divergence checker and the shared compile-and-hash routine are
  out of scope (roadmap tasks 4.1.2 and 3.1.2). Rationale: roadmap 4.1.1
  "Requires phase 2" and describes only the write ("Concatenate chapter drafts …
  writing `working/manuscript/compiled.md` atomically, and exit 3 when the
  chapter manifest is absent or empty"); 4.1.2 "Requires 4.1.1 and 3.1.2" and
  owns `--check` "by calling the shared compile-and-hash routine from 3.1.2".
  Phase 3 (`novel-done`, 3.1.1/3.1.2) is unbuilt (`novel_compile` and
  `novel_done` are still stubs in `novel_ralph_skill/commands/stub.py`), so
  4.1.1 must not depend on the hash routine. The Cyclopts app is therefore a
  single default callback now; 4.1.2 extends it with `--check`. Date/Author:
  2026-06-24, planning agent.

- Decision (D-WRITER): the atomic write of `compiled.md` reuses the
  temp-file-plus-`Path.replace` *discipline* of
  `write_document_atomically` but through a new text-twin
  `write_text_atomically(text: str, path: Path) -> None` in
  `novel_ralph_skill/state/document.py`. Rationale: `write_document_atomically`
  is TOML-specific (it calls `tomlkit.dumps(document)`), whereas `compiled.md` is
  a pre-rendered plain string. A thin text twin keeps the temp-file/rename/unlink
  discipline in one module (no second atomic-write pattern), is re-exported from
  the `state` package, and `write_document_atomically` is refactored to delegate
  to it so the two share one implementation (a separate atomic refactor commit if
  the delegation grows the diff — AGENTS.md "Separate atomic refactors").
  Alternative rejected: copying the temp-file dance into the command module
  (duplicates the §3.4 discipline). Date/Author: 2026-06-24, planning agent.

- Decision (D-EMPTY): an **empty** `[chapters]` manifest (`state.chapters == ()`)
  is the exit-`3` refusal, identical to an **absent** one. Rationale: design §10
  lines 811-815 name "`[chapters]` is absent or empty" as one failure mode — no
  authoritative ordering exists either way. The typed `State` parser yields an
  empty tuple for an empty/absent `[chapters]` table, so the body refuses on
  `not state.chapters`. A pre-drafting tree (e.g. `premise` phase) has an empty
  manifest and so cannot compile, which is correct: compilation belongs to
  drafting/final-pass. Date/Author: 2026-06-24, planning agent.

- Decision (D-PT): `novel-compile` performs a single atomic `compiled.md` write
  and opens no `[pending_turn]` bracket. Rationale: it writes one file, already
  atomic via `Path.replace`; the §3.4 bracket is for multi-file turns. This
  mirrors task 2.3.1's D-PT for `recount`. `docs/developers-guide.md` mis-lists
  `novel-compile` as bracketed in two places (`:205-208`, `:596`); Work item 3
  corrects both, citing design §4.3/§3.4, exactly as 2.3.1 corrected the
  `recount` mis-listings. Date/Author: 2026-06-24, planning agent.

- Decision (D-PT-DESIGN): the design is **not** edited by this task; only the
  developers' guide is corrected. Rationale: design §4.3 (single `compiled.md`
  output) and §3.4 (the bracket framing) already make the single-file reading
  authoritative; §3.4 line 256's loose "each mutator opens a `[pending_turn]`"
  phrasing is governed by the more specific §4.3, exactly as task 2.3.1 recorded
  for `recount`. Editing the design is out of scope here. Date/Author:
  2026-06-24, planning agent.

- Decision (D-CUPRUM): no cuprum API is pinned or used. Rationale:
  `novel-compile` is pure file I/O over `pathlib` plus the in-package
  `concatenate_drafts`; design §4 lines 267-270 state no v1 command invokes an
  external process for its core logic. The locked cuprum (`0.1.0`, `uv.lock`
  lines 113-118) catalogue/`Program`/`sh` surface is verified present
  (`/data/leynos/Projects/cuprum/cuprum/catalogue.py`,
  `tests/test_console_scripts_e2e.py:30-31,73-84` allowlists an absolute-path
  `Program` and runs `sh.make(...)().run_sync(...)`), but it is exercised only by
  the existing wheel-build e2e test, not by this command. Recorded so a reviewer
  does not expect a cuprum citation in the command body. Date/Author:
  2026-06-24, planning agent.

- Decision (D-CWD): the new unit, property, and BDD tests must
  `monkeypatch.chdir(working.parent)` before invoking `novel-compile`. Rationale:
  the command resolves a **cwd-relative** `working/` directory and
  `working/state.toml`, exactly like `novel-state`/`recount`/`desloppify`
  (`novel_ralph_skill/commands/novel_state.py:85-96`). The existing mutator and
  recount tests are emphatic that the chdir must precede the call
  (`tests/test_recount_e2e.py:62`). The new tests inherit this; calling it out
  prevents a flaky "state.toml not found" failure that would look like a compile
  bug. Date/Author: 2026-06-24, planning agent.

- Decision (D-RESULT): the write success `result` is
  `{"compiled": "working/manuscript/compiled.md", "chapters": <int>, "bytes":
  <int>}`. Rationale: a mutator names what it changed (design §3.3) — the path it
  wrote, how many chapters it concatenated, and the byte length of the output —
  a fixed, bounded payload that does not grow with chapter count (mirroring
  `novel-done`'s bounded-result discipline, design §4.2 lines 345-348). The path
  is the working-relative string (not an absolute path) so the envelope is
  deterministic for snapshotting (AGENTS.md snapshot redaction rule).
  Date/Author: 2026-06-24, planning agent.

## Outcomes & retrospective

Delivered as planned. `novel-compile` is a deterministic, manifest-ordered write:
it concatenates the chapter drafts in ascending zero-padded chapter-index order
via the single production `concatenate_drafts`/`present_draft_bodies` rules, and
the round-trip-oracle test confirms its output is accepted by the
`compiled-matches-drafts` disk-evidence invariant (so a freshly compiled tree is
coherent under `novel-state check`). It refuses an absent/empty manifest — and a
missing `state.toml`, an undecodable draft, or an absent `manuscript/` — with exit
`3`, leaving any prior `compiled.md` intact; it is byte-identical on re-run
(pinned by a unit test, the Hypothesis property, and the BDD idempotence step).

Outcome against the three Constraints worth flagging:

- **D-READ (read-rule reuse):** delivered by *promoting* the shared
  `present_draft_bodies` rather than wrapping it, so the write path and the
  detector are literally the same function — the strongest form of the
  "draft-body read rule matches the disk-evidence detector exactly" Constraint.
- **D-WRITER (one atomic-write pattern):** delivered;
  `write_document_atomically` delegates to the new `write_text_atomically`, so no
  second temp-file dance exists.
- **D-PT (no bracket):** delivered, and the developers' guide mis-listings are
  corrected; the design was not edited (D-PT-DESIGN holds).

Tolerances respected: the production change is the small `_compile.py` module
plus the promoted read rule and the text writer (well under the ~220-line / 5-file
ceiling); no existing public signature changed; no cuprum/subprocess surface was
added (D-CUPRUM); and the `--check`/hash scope creep (D-SCOPE) was avoided.

Lesson for the next agent: `make fmt` reflows every markdown file in the repo
(mdformat), which both breaches the per-file MD013 wrap and churns dozens of
unrelated docs. Gate with `make all` and run `make markdownlint`/`make nixie`
directly on the files you touched; do **not** run `make fmt` on this repo unless
you intend the global reflow (the spurious churn was stashed aside, matching the
many prior "spurious make-fmt mdformat churn" stashes on this repo).

## Context and orientation

This repository is the `novel-ralph` harness: a set of Cyclopts console commands
that manage a novel-in-progress under a cwd-relative `working/` tree. State lives
in `working/state.toml`; the manuscript lives under `working/manuscript/`. Five
console-scripts form the v1 spine (`novel-state`, `novel-done`, `novel-compile`,
`desloppify`, `wordcount`); `novel-state` and `desloppify` are real, the other
three are stubs that exit `2` (`novel_ralph_skill/commands/stub.py`). This task
makes `novel-compile` real (the write path).

Definitions:

- **Mutator**: a command that writes to disk, as opposed to a *checker*
  (read-only). `novel-compile` (write) is a mutator; `novel-compile --check`
  (task 4.1.2) is a checker (design §3.3).
- **Chapter manifest**: the `[chapters]` table in `state.toml` — an ordered
  record of each planned chapter (number, slug, title, target words). The typed
  view is `state.chapters: tuple[ChapterEntry, ...]` (design §5.1).
- **Zero-padded chapter index**: the directory name `chapter-NN` where `NN` is
  the manifest chapter number padded to two digits (`f"chapter-{number:02d}"`).
- **`DRAFT_SEPARATOR`**: the single `"\n\n"` separator the ordered draft bodies
  are joined with (`novel_ralph_skill/state/compile_model.py:30`).
- **Exit `3`**: the state/input-error exit code (ADR-003; design §3.2), raised by
  `StateInputError`; distinct from the benign `1` the harness loops on.

Key files (full repository-relative paths):

- `docs/novel-ralph-harness-design.md` — the design. §3.1 (envelope), §3.2 (exit
  codes), §3.3 (command/query segregation; the mutator/checker table at lines
  240-243), §3.4 (atomic writes / `[pending_turn]`), §4 lines 265-273 (the
  spine; no external process), §4.3 (`novel-compile`, lines 350-374), §5.1
  (schema; `[chapters]` manifest lines 418-424), §5.2 (the
  manifest-disk-bijection invariant lines 477-482), §9 (verification), §10
  (failure modes; manifest-missing lines 811-815).
- `docs/adr-003-shared-interface-contract.md` — the envelope and the
  disambiguated exit-code table (exit `3` state/input; exit `4` actionable).
- `docs/adr-005-command-surface-five-scripts.md` — five named commands, each 1:1
  onto a deterministic operation (so `novel-compile` is a single default command).
- `docs/scripting-standards.md` — Cyclopts, cuprum, and pathlib conventions
  (atomic temp-file-plus-`Path.replace`).
- `docs/developers-guide.md` — the contract narrative; the compile-and-hash claim
  (lines 301-305), the checker/mutator segregation and `[pending_turn]`
  paragraph (lines 202-208), the twin policy (lines 453-485), and the single-file
  `recount`/`reconcile`/`novel-compile` note (line 596).
- `docs/users-guide.md` — the installed-command list (lines 76-90, 170);
  `novel-compile` is currently listed as a stub.
- `docs/execplans/roadmap-2-3-1.md` — the `recount` plan, the closest precedent:
  the single-file write, the exit-`3` fault routing, the D-PT guide correction,
  and the D-CUPRUM/D-CWD decisions this plan mirrors.
- `novel_ralph_skill/state/compile_model.py` — `DRAFT_SEPARATOR` and
  `concatenate_drafts` (the production join rule this task reuses; lines 26-53).
- `novel_ralph_skill/state/disk_evidence.py` — `_present_draft_bodies` (lines
  164-176, the manifest-driven draft-body read rule) and
  `_check_compiled_matches_drafts` (lines 179-196, the ready oracle for the
  round-trip).
- `novel_ralph_skill/state/_disk_paths.py` — `_chapter_dir_name` (lines 19-21).
- `novel_ralph_skill/state/document.py` — `load_document`,
  `write_document_atomically` (lines 114-151, the atomic-write discipline the
  text twin reuses), `_TEMP_PREFIX`.
- `novel_ralph_skill/state/__init__.py` — the `state` package's public surface
  (re-exports `concatenate_drafts`, `DRAFT_SEPARATOR`, `load_state`,
  `write_document_atomically`, `State`, `ChapterEntry`); the text writer is added
  to this surface.
- `novel_ralph_skill/state/parse.py` / `schema.py` — `load_state`, the typed
  `State` and `ChapterEntry` shapes (`state.chapters`).
- `novel_ralph_skill/commands/novel_state.py` — `WORKING_DIR_NAME`,
  `working_dir()`, `state_path()`, `STATE_INPUT_ERRORS`, `_load_or_state_error`
  (lines 85-153, the shared cwd-relative resolvers and the exit-`3` boundary the
  command reuses).
- `novel_ralph_skill/commands/_recount.py` — the closest body precedent (the
  exit-`3` read-fault wrapper `_recount_or_state_error`, lines 43-81).
- `novel_ralph_skill/commands/_desloppify.py` — the closest *default-callback*
  command precedent (a single-purpose Cyclopts app driven through `run`).
- `novel_ralph_skill/commands/stub.py` — the entry points;
  `novel_compile()` (lines 98-100) is the stub this task replaces with a real
  driver (mirroring `desloppify()` at lines 103-123).
- `novel_ralph_skill/commands/names.py` — `COMMAND_NAMES`/`COMMAND_ENTRY_POINTS`
  (the single source of truth; `"novel-compile": "novel_compile"`).
- `novel_ralph_skill/contract/runner.py` — `run`, `RunContext`,
  `CommandOutcome`, `StateInputError`, `parse_global_flags`.
- `novel_ralph_skill/contract/envelope.py` / `exit_codes.py` — the envelope and
  the `ExitCode` enum.
- `tests/working_corpus/_specs.py` — `WorkingTreeSpec`, `ChapterSpec`,
  `chapter_dir_name`, `draft_body`, `concatenate_drafts` (the corpus join twin,
  lines 217-227), `COMPILED_AUTO`.
- `tests/working_corpus/_builder.py` — `build_working_tree(spec, dest)` (line
  181) materializes a `working/` tree on disk.
- `tests/working_corpus/_library.py` — `PHASE_STATES`, `COHERENT_BASELINE` (the
  drafting/final-pass/done specs that carry a coherent `compiled.md`).
- `tests/conftest.py` — re-exposes the corpus as fixtures.
- `tests/test_recount_e2e.py`, `tests/features/recount.feature`,
  `tests/steps/recount_steps.py`, `tests/test_novel_state_mutator_snapshots.py`,
  `tests/test_console_scripts_e2e.py` — the patterns the new tests mirror.

## Plan of work

Three ordered, independently committable, gate-passable work items. Each ends
with `make all` green (plus `make markdownlint` and `make nixie` for the markdown
work in Work item 3).

### Work item 1 — Add the shared atomic text writer

Goal: one pure function that writes a pre-rendered string to a path atomically,
sharing the temp-file/rename/unlink discipline with the existing TOML writer, so
no second atomic-write pattern is introduced.

Documentation to read first: design §3.4 (lines 245-251, the atomic-write rule);
`docs/scripting-standards.md` (the `pathlib` atomic-write convention);
`novel_ralph_skill/state/document.py:114-151` (`write_document_atomically`).

Skills to load: `python-router` → `python-abstractions` (the context-manager /
helper shape) and `python-errors-and-logging` (the unlink-on-failure path); use
`leta` for navigation (`leta show novel_ralph_skill.state.document`,
`leta refs write_document_atomically`) and `sem` for history if needed.

Edits:

1. In `novel_ralph_skill/state/document.py`, add
   `write_text_atomically(text: str, path: Path) -> None`: it writes `text` to a
   `NamedTemporaryFile("w", delete=False, dir=path.parent, prefix=_TEMP_PREFIX,
   suffix=".tmp", encoding="utf-8")`, closes the handle, then
   `temp_path.replace(path)`, unlinking the temp file on any `OSError` before
   re-raising — the exact discipline `write_document_atomically` already uses.
   Refactor `write_document_atomically` to delegate:
   `write_text_atomically(tomlkit.dumps(document), path)`, so the temp-file dance
   lives in one place (D-WRITER). If the delegation refactor would noticeably
   grow the Work item 1 diff, land the new function first (with its tests) and do
   the delegation as a *separate* atomic refactor commit (AGENTS.md "Separate
   atomic refactors").
2. Re-export `write_text_atomically` from `novel_ralph_skill/state/__init__.py`
   (add the import and the `__all__` entry).

Tests to add:

- `tests/test_state_document.py` (extend): `write_text_atomically` writes the
  exact bytes; a second write overwrites atomically; on a write to a `path` whose
  parent does not exist it raises `OSError` and leaves no temp file behind (assert
  no `.state.toml.*` temp file survives in the directory); the existing
  `write_document_atomically` round-trip tests still pass after the delegation
  refactor. Keep the snapshot-free, byte-level assertions of the existing module.

Validation: `make all` green; confirm red-before-green by temporarily writing to
`path` directly (no temp file) and observing the leaked-temp-file assertion fail,
then revert.

Acceptance: `write_text_atomically` exists, is re-exported, and the document-writer
tests pass; `write_document_atomically` behaviour is unchanged.

### Work item 2 — Implement the `novel-compile` write body

Goal: the `novel-compile` body that loads the state, refuses an empty/absent
manifest with exit `3`, reads each manifest chapter's `draft.md` in ascending
chapter order, concatenates with `DRAFT_SEPARATOR`, and writes
`working/manuscript/compiled.md` atomically — returning a write-shaped
`CommandOutcome`.

Documentation to read first: design §4.3 (lines 350-374), §3.2, §3.4, §10 (lines
811-815); `novel_ralph_skill/commands/_recount.py` in full (the exit-`3`
read-fault wrapper);
`novel_ralph_skill/state/disk_evidence.py:164-196` (`_present_draft_bodies`,
`_check_compiled_matches_drafts`).

Skills to load: `python-router` → `python-errors-and-logging` (narrow `except`,
`raise … from`, the exit-`3` channel), `python-iterators-and-generators` (the
ordered body aggregation), and `python-types-and-apis` (the `CommandOutcome`
signature); then `python-verification` → `hypothesis` for the
deterministic-round-trip property (a concrete oracle —
`_check_compiled_matches_drafts` — exists, so Hypothesis fits, not CrossHair);
`leta` for navigation.

Edits — create `novel_ralph_skill/commands/_compile.py`:

1. Add a module-private helper `_present_draft_bodies(state, manuscript_dir)` —
   OR import and reuse the disk-evidence one. **Prefer reuse:** promote
   `novel_ralph_skill.state.disk_evidence._present_draft_bodies` to a shared,
   re-exported helper (rename to drop the leading underscore, re-export from the
   `state` package, update the one internal caller), so the compile read rule and
   the `compiled-matches-drafts` read rule are *literally the same function*
   (Constraints "Draft-body read rule matches the disk-evidence detector
   exactly"). If promotion grows the diff past tolerance, instead add a thin
   wrapper in `compile_model.py` that both call and pin them equal by test —
   escalate the choice if it materially changes behaviour (Tolerances). Record
   the chosen path in the Decision Log.
2. Add `compile_manuscript() -> CommandOutcome`:
   - Resolve `path = state_path()` and `root = working_dir()` from
     `novel_ralph_skill.commands.novel_state` (the cwd-relative resolvers).
   - `state = _load_or_state_error(path)` (reuse the exit-`3` boundary).
   - If `not state.chapters`: `raise StateInputError("cannot compile: chapter
     manifest is absent or empty")` (exit `3`; D-EMPTY).
   - Read the ordered bodies via the shared read rule, wrapped in
     `except STATE_INPUT_ERRORS as exc: raise StateInputError(...) from exc`
     (mirroring `_recount_or_state_error`), so an undecodable/unreadable draft is
     exit `3`.
   - `rendered = concatenate_drafts(bodies)`.
   - `compiled_path = root / "manuscript" / "compiled.md"`; write via
     `write_text_atomically(rendered, compiled_path)` (wrap in the same
     `STATE_INPUT_ERRORS` boundary so an absent `manuscript/` is exit `3`).
   - Return `CommandOutcome(code=ExitCode.SUCCESS, result={"compiled":
     "working/manuscript/compiled.md", "chapters": len(state.chapters), "bytes":
     len(rendered.encode("utf-8"))}, messages=[f"compiled {len(state.chapters)}
     chapters into working/manuscript/compiled.md"])` (D-RESULT). No `violations`
     key; no `[pending_turn]` bracket (D-PT).
3. Add `build_app() -> cyclopts.App`: a single-default-callback Cyclopts app
   (`result_action="return_value", exit_on_error=False, print_error=False,
   help_on_error=False`, the `run`-wrapper contract), whose `@app.default`
   returns `compile_manuscript()`. Mirror `_desloppify.build_app`'s wiring; the
   `--check` flag is **not** added (D-SCOPE).

Tests to add:

- `tests/test_compile_unit.py` (unit): over a coherent drafting tree
  (`wc.build_working_tree` with two or three drafted chapters whose hand-typed
  bytes differ from `compiled.md` or omit it), `compile_manuscript()` returns
  exit `0`, a write-shaped `result` (no `violations`), and writes
  `working/manuscript/compiled.md` equal to `concatenate_drafts` of the ordered
  draft bodies; a second call leaves `compiled.md` byte-for-byte identical
  (determinism). An **empty-manifest** tree (a pre-drafting `PHASE_STATES`
  member, e.g. `premise`) refuses with exit `3` and writes no `compiled.md`. A
  **missing** `state.toml` refuses with exit `3`. An **undecodable** `draft.md`
  (write `b"\xff\xfe"` into a chapter draft) refuses with exit `3` and leaves any
  prior `compiled.md` intact. An **absent** `draft.md` for a manifest chapter
  contributes the empty string and the compile still succeeds (pins the
  `FileNotFoundError`-as-empty-string boundary against the
  `UnicodeDecodeError`-as-exit-`3` one). Each test
  `monkeypatch.chdir(working.parent)` first (D-CWD).
- `tests/test_compile_unit.py` (round-trip oracle): after
  `compile_manuscript()` over a coherent tree, `check_disk_evidence(load_state(
  state_path()), working_dir())` reports **no** `compiled-matches-drafts`
  violation — i.e. a freshly compiled tree is coherent under the disk-evidence
  detector (Risk "output diverges from `compiled-matches-drafts`"). This is the
  load-bearing pin that the write path and the invariant agree.
- `tests/test_compile_unit.py` (ordering): a tree whose chapter directories are
  created out of order on disk (build chapters in a shuffled order) still compiles
  in ascending manifest order — assert the output equals the manifest-ordered
  concatenation, not a glob-ordered one (Risk "non-deterministic write").
- Property (Hypothesis): over a generated populated manifest of chapter numbers
  (contiguous from 1) and per-chapter word counts materialized with
  `draft_body`, `compile_manuscript()` succeeds and the written `compiled.md`
  equals `DRAFT_SEPARATOR.join(ordered draft bodies)`, and re-running yields
  identical bytes. Mirror the `@settings`/`function_scoped_fixture`-suppression
  style of `tests/test_state_wordcount.py`. The property must
  `monkeypatch.chdir(working.parent)` before each call (D-CWD).

Validation: `make all` green. Confirm red-before-green by temporarily joining
with `"\n"` instead of `DRAFT_SEPARATOR` (the round-trip oracle and the equality
tests go red), then revert.

Acceptance: `compile_manuscript`/`build_app` exist; the write produces an output
the `compiled-matches-drafts` invariant accepts; empty/absent manifest and read
faults refuse with exit `3`; the property pins determinism.

### Work item 3 — Wire the entry point, BDD scenario, snapshot, e2e, and guides

Goal: drive `novel-compile` through the installed console-script path, prove the
end-to-end behaviour and the roadmap success criteria with a behavioural scenario
and a machine-mode envelope snapshot, and document the command.

Documentation to read first: `novel_ralph_skill/commands/stub.py:103-123`
(`desloppify()`, the real-app entry-point pattern); `tests/test_recount_e2e.py`
(the entry-point reachability pattern); `tests/features/recount.feature` +
`tests/steps/recount_steps.py` (the BDD pattern);
`tests/test_novel_state_mutator_snapshots.py` (the snapshot pattern);
`tests/test_console_scripts_e2e.py` (the wheel-build e2e and its cuprum usage);
`docs/users-guide.md`, `docs/developers-guide.md`; AGENTS.md "Snapshot tests" and
"end-to-end tests" rules.

Skills to load: `python-router` → `python-testing` (pytest-bdd, syrupy snapshot
discipline); `en-gb-oxendict` for the guide prose; `leta` for navigation.

Edits:

1. `novel_ralph_skill/commands/stub.py`: replace the `novel_compile()` stub body
   with a real driver mirroring `desloppify()` — `human, residual =
   parse_global_flags(sys.argv[1:])`, import `_compile`, then `run(
   _compile.build_app(), residual, RunContext(command=_NAME_FOR["novel_compile"],
   working_dir=WORKING_DIR_NAME, human=human))`. Update the module docstring's
   "stub" list so `novel-compile` is named as delivered (and `novel-done`/
   `wordcount` remain the only stubs).
2. `tests/test_compile_e2e.py` (new): a fast entry-point reachability test
   mirroring `tests/test_recount_e2e.py` — drive `stub.novel_compile()` against
   a prepared drafting tree with `sys.argv = ["novel-compile"]`, assert exit `0`,
   parse the envelope, and assert `result["compiled"] ==
   "working/manuscript/compiled.md"` and `compiled.md` exists with the expected
   bytes. Add an exit-`3` reachability case (empty-manifest tree → exit `3`).
3. `tests/test_console_scripts_e2e.py` (extend if it already drives subcommands):
   confirm `novel-compile` is reachable through the installed wheel and exits the
   contract code on a prepared tree. If extending the wheel-build path is heavier
   than the fast entry-point test already proves, keep the wheel test scoped to
   reachability and rely on `test_compile_e2e.py` for behaviour (note the choice
   in Progress).
4. `tests/features/compile.feature` + `tests/steps/compile_steps.py`: a scenario
   that, given a drafting tree with two or three drafted chapters and a stale or
   absent `compiled.md`, runs `novel-compile`, then asserts exit `0`, that
   `working/manuscript/compiled.md` equals the manifest-ordered concatenation, and
   that a second `novel-compile` leaves `compiled.md` byte-for-byte unchanged
   (the roadmap determinism success criterion). Add a second scenario: an
   empty-manifest tree → exit `3`, no `compiled.md` written. Register with
   `scenarios("../features/compile.feature")`; the run step
   `monkeypatch.chdir`s into the prepared tree's parent (D-CWD).
5. `tests/test_compile_snapshots.py` (new) or extend an existing snapshot module:
   a `novel-compile` success-envelope snapshot with nondeterministic fields
   normalised (the `compiled` path is the working-relative token, not an absolute
   path; `working_dir` is `"working"`), paired with a semantic assertion on the
   exit code, `ok`, and the `chapters`/`bytes` values (AGENTS.md "pair them with
   semantic assertions"). Keep the snapshot to the stable envelope boundary, not
   a raw dump.
6. Documentation:
   - `docs/users-guide.md`: move `novel-compile` out of the "still stubs" list
     (lines 87-90) and add a short subsection: it regenerates
     `working/manuscript/compiled.md` by concatenating the chapter drafts in
     zero-padded chapter-index order, writes nothing and exits `3` when the
     manifest is absent or empty, and is deterministic/idempotent. Cite the
     exit-code table already in that file.
   - `docs/developers-guide.md`: (a) correct the `[pending_turn]` mis-listing at
     `:205-208` and `:596` so `novel-compile` is named a **single-file**
     `Path.replace` writer with **no** bracket (only genuinely multi-file writers
     — `reconcile` — bracket), citing design §4.3/§3.4 (D-PT); (b) update the
     compile-and-hash sentence at `:301-305` to note that the **write** path
     (task 4.1.1) reuses `compile_model.concatenate_drafts`, while the
     `--check`/`novel-done` **hash** routine is task 4.1.2/3.1.2 (do not claim
     `--check` is delivered). After the edits, grep the guide for `novel-compile`
     and confirm no remaining sentence implies it is multi-file/bracketed or that
     `--check` exists.

Tests/validation for this item: `make all` (Python gates), **plus**
`make markdownlint` and `make nixie` for the guide edits (AGENTS.md markdown
rules; no Mermaid is added, but `nixie` is run per the standing rule for markdown
changes).

Acceptance: `tests/features/compile.feature` passes (both scenarios green), the
`novel-compile` snapshot is committed and semantically asserted, the entry-point
and e2e reachability checks pass, and both guides build clean under
`make markdownlint`/`make nixie`.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-4-1-1`.

```console
$ git branch --show-current
roadmap-4-1-1
```

Per work item, after edits:

```console
$ make all
... build check-fmt lint typecheck test all pass ...
```

Expect the Python gates (`build check-fmt lint typecheck test`) to pass. For Work
item 3's markdown:

```console
$ make markdownlint
Summary: 0 error(s)
$ make nixie
... no Mermaid diagrams; exits clean ...
```

Use `make fmt` to apply Ruff + mdformat fixes before `check-fmt`.

To prove a new test is meaningful (red-before-green), run just that test before
implementing the production change:

```console
$ UV_CACHE_DIR=.uv-cache uv run pytest -q tests/test_compile_unit.py
... fails before Work item 2's edit; passes after ...
```

Expect a failure (the body does not yet exist) before Work item 2's edit and a
pass after. Mirror this for the writer (Work item 1) and the BDD scenario.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes; the new `tests/test_state_document.py` writer cases,
  `tests/test_compile_unit.py` (unit + round-trip-oracle + ordering + property),
  `tests/test_compile_e2e.py`, `tests/features/compile.feature`, and the
  `novel-compile` envelope snapshot all pass. Each new test fails before its
  production change and passes after.
- Lint/typecheck: `make lint` (Ruff, interrogate 100% docstrings, Pylint) and
  `make typecheck` (`ty check`) pass over `novel_ralph_skill tests`.
- Formatting: `make check-fmt` passes (`make fmt` to fix).
- Markdown (Work item 3): `make markdownlint` and `make nixie` pass.
- Audit: `make audit` (`pip-audit`) passes — no new dependency is added.

Behavioural acceptance (a human can verify):

- On a tree with `working/manuscript/chapter-01/draft.md`,
  `chapter-02/draft.md`, `chapter-03/draft.md` and a populated `[chapters]`
  manifest, running `novel-compile` exits `0` and writes
  `working/manuscript/compiled.md` as the three drafts joined by a blank line, in
  ascending chapter order. A second `novel-compile` yields a byte-for-byte
  identical `compiled.md`.
- Immediately after a successful `novel-compile`, `novel-state check` reports no
  `compiled-matches-drafts` violation.
- On a tree with an empty or absent `[chapters]` manifest (e.g. a `premise`-phase
  tree), `novel-compile` exits `3` and writes no `compiled.md`.

## Idempotence and recovery

Every step is re-runnable. `novel-compile` is itself deterministic by
construction (second run over unchanged drafts and manifest yields identical
bytes — pinned by test). The atomic `write_text_atomically` leaves either the
prior or the new `compiled.md`, never a torn file; a failed write unlinks its
temp file. Tests use `tmp_path`-scoped working trees, so reruns do not accumulate
state. No destructive operation is introduced; `novel-compile` never deletes a
`working/` file.

## Artifacts and notes

The load-bearing production join rule the compile output is pinned against:

```python
# novel_ralph_skill/state/compile_model.py:30,33-53
DRAFT_SEPARATOR = "\n\n"

def concatenate_drafts(drafts: cabc.Sequence[str]) -> str:
    return DRAFT_SEPARATOR.join(drafts)
```

The ready oracle (the disk-evidence invariant) the round-trip is verified
against:

```python
# novel_ralph_skill/state/disk_evidence.py:179-196
def _check_compiled_matches_drafts(state, working_dir):
    compiled = working_dir / "manuscript" / "compiled.md"
    if not compiled.exists():
        return None
    expected = concatenate_drafts(_present_draft_bodies(state, working_dir))
    if compiled.read_text(encoding="utf-8") == expected:
        return None
    return Violation(invariant=COMPILED_MATCHES_DRAFTS, ...)
```

## Interfaces and dependencies

Libraries/modules to use and why:

- `pathlib` — directory joins and `draft.md` reads, and the atomic
  temp-file-plus-`Path.replace` write.
- `tempfile.NamedTemporaryFile` — the in-directory temp file for the atomic
  write (the discipline shared with `write_document_atomically`).
- `cyclopts` — the single-default-callback app, wired to the shared `run`
  wrapper.
- `novel_ralph_skill.state` — `load_state`, `State`, `ChapterEntry`,
  `concatenate_drafts`, `DRAFT_SEPARATOR`, the shared draft-body read helper, and
  the new `write_text_atomically`.
- `novel_ralph_skill.commands.novel_state` — `WORKING_DIR_NAME`, `working_dir`,
  `state_path`, `STATE_INPUT_ERRORS`, `_load_or_state_error`.
- `novel_ralph_skill.contract.runner` — `CommandOutcome`, `StateInputError`,
  `RunContext`, `run`, `parse_global_flags`.
- `novel_ralph_skill.contract.exit_codes` — `ExitCode`.
- No new external dependency. No cuprum surface (Decision Log D-CUPRUM).

Signatures that must exist at the end:

```python
# novel_ralph_skill/state/document.py
def write_text_atomically(text: str, path: Path) -> None: ...

# novel_ralph_skill/commands/_compile.py
def compile_manuscript() -> CommandOutcome: ...
def build_app() -> cyclopts.App: ...
```

`novel_ralph_skill/commands/stub.py`'s `novel_compile()` entry point is rewired
from the stub to a real `run`-driven driver; its signature (zero-argument entry
point) is unchanged. No existing public signature changes.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from later
reviews and audits of the `novel-compile` write path. Execute each as a small
addendum pass — no plan or design-review cycle: make the change, run `make all`
(plus `make markdownlint`/`make nixie` for Markdown), `coderabbit review
--agent`, commit, and tick the matching roadmap sub-task on merge. Substantial,
cross-cutting hygiene from the same audit (the `manuscript_dir`/`compiled_path`
accessor consolidation, audit:4.1.1 Finding 1) is re-routed to roadmap step 7.10
rather than folded here.

- [x] 4.1.1.1 — Add a coherence integration test that drives `novel-compile`
  then `novel-state check` end-to-end through the installed console scripts
  (from review:4.1.1, low). The round-trip oracle is pinned at the function
  level (`check_disk_evidence` over a freshly compiled tree); a thin integration
  test invoking both real entry points in sequence catches future drift between
  the two commands' resolvers and envelopes that the function-level pin cannot
  see. The function-level pin already covers the load-bearing invariant, so this
  is defence-in-depth. Gate with `make all`.
