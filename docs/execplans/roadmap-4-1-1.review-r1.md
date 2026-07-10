# Logisphere adversarial design review — roadmap 4.1.1 (Round 1)

Reviewer: Logisphere crew (adversarial design review). Verdict source of truth:
the StructuredOutput returned to the orchestrator. This file is the working note.

## Verdict

PROCEED WITH CONDITIONS — no blocking defects. The plan is implementable and
design-conformant as written. Every load-bearing factual claim was verified
against real source (not the planner's summary). The advisory items below would
strengthen the plan but do not block implementation.

## What was verified against real source

- `compile_model.DRAFT_SEPARATOR == "\n\n"` and `concatenate_drafts` shape
  (`novel_ralph_skill/state/compile_model.py:30,33-53`). Matches the plan.
- The round-trip oracle `_check_compiled_matches_drafts` recomputes
  `concatenate_drafts(_present_draft_bodies(state, working_dir))`
  (`disk_evidence.py:179-196`). The plan's "ready oracle" claim holds; a compile
  that reuses both functions is accepted by the invariant by construction.
- `_present_draft_bodies` reads `draft.read_text("utf-8") if draft.exists() else
  ""` ordered by ascending `chapter.number` (`disk_evidence.py:164-176`). The
  plan's read-rule constraint is accurate.
- The atomic-write discipline and `_TEMP_PREFIX = ".state.toml."`
  (`document.py:57,114-151`). The text-twin D-WRITER plan is faithful.
- Exit-3 routing precedent: `_recount._recount_or_state_error`
  (`_recount.py:43-81`) and, more closely, `_desloppify.source_chapters`
  (`_desloppify.py:158-203`) already import `STATE_INPUT_ERRORS`,
  `WORKING_DIR_NAME`, `_load_or_state_error` from `novel_state` and wrap draft
  reads in `except STATE_INPUT_ERRORS … raise StateInputError … from exc`. The
  plan's body recipe is in-repo precedent, not invention.
- Single-default-callback Cyclopts app through `run`: `_desloppify.build_app`
  (`_desloppify.py:290-320`) is the exact pattern, with
  `result_action="return_value", exit_on_error=False, print_error=False,
  help_on_error=False`. cyclopts is locked at 4.18.0 (`uv.lock:137-148`). No
  uncited memory-based cyclopts claim is made — the plan leans on working code.
- D-EMPTY: `PHASE_STATES["premise"]` has `chapters=()`
  (`tests/working_corpus/_library.py:67-76`); `drafting`/`COHERENT_BASELINE` has
  a populated manifest and `compiled=None` (`_library.py:79-97,118`). The
  empty-manifest refusal and the "coherent drafting tree without compiled.md"
  unit fixture both materialize directly. `parse._chapters` yields an empty
  tuple for an absent/empty `[chapters]` (`parse.py:87-103`), so `not
  state.chapters` is the correct refusal predicate.
- D-CWD: `monkeypatch.chdir(working.parent)` is the established e2e pattern
  (`tests/test_recount_e2e.py:62`).
- Path helper `_chapter_dir_name` exists (`_disk_paths.py:19-21`).
- Entry-point registry `"novel-compile": "novel_compile"`
  (`names.py:24`); the `novel_compile()` stub to replace is at `stub.py:98-100`
  and the real-driver model is `desloppify()` at `stub.py:103-123`.
- cuprum is locked at 0.1.0 (`uv.lock:113-118`); D-CUPRUM ("no cuprum surface
  added") is trivially true — the command is pure pathlib + in-package
  `concatenate_drafts`.
- The corpus builder `build_working_tree(spec, dest) -> Path`
  (`_builder.py:181`) writes `compiled.md` only when the spec sets it
  (`_builder.py:205-207`), so a `drafting` fixture starts without one.

## Documentation defects the plan correctly targets (verified accurate)

- `docs/developers-guide.md:207-208` and `:596` list `novel-compile` among the
  genuinely-multi-file `[pending_turn]` writers (grouped with `reconcile`). This
  is a real mis-listing; the plan's D-PT correction is warranted.
- `docs/developers-guide.md:303-304` asserts `novel-done` and `novel-compile
  --check` "call the same compile-and-hash routine" — implies `--check` is
  delivered. The plan's edit to scope this to the write path (4.1.1) vs the hash
  routine (4.1.2/3.1.2) is correct.
- `docs/users-guide.md:87` lists `novel-compile` as a stub; the plan moves it.

## Design-conformance: the single-file / no-bracket call (D-PT, D-PT-DESIGN)

This is the one place the design text is in genuine tension, so it was
scrutinized. Design §3.4 lines 255-256 say "each mutator opens a `[pending_turn]`
intent record … before it touches any other file." Taken literally that would
bracket every mutator. But:

- §3.4's rationale is explicitly multi-file atomicity ("a turn that touches
  several files … is not atomic as a whole"). `novel-compile` writes exactly one
  file (`compiled.md`), already atomic via `Path.replace`.
- The §3.3 mutator table names only `compiled.md` as `novel-compile`'s write.
- §4.3 names only `compiled.md` as the output.
- The codebase already realizes this reading: `recount`/`set-cursor`/
  `advance-phase` write a single file and open NO bracket (`_recount.py`,
  `_state_mutators.py`), and the dev guide already names `recount` single-file
  (`:596`). Task 2.3.1's D-PT set exactly this precedent.
- No per-turn `log.md` append exists anywhere in the commands package (grep:
  only `init` writes `log.md`, once, empty). So there is no hidden second file
  that would make `novel-compile` multi-file and reopen the bracket question.

Conclusion: the plan's single-file, no-bracket reading is design-conformant and
consistent with merged precedent. Not a defect.

## Advisory (non-blocking) — would strengthen the plan

1. The `_present_draft_bodies` reuse is left as a two-way fork in Work item 2
   edit 1 (promote-and-re-export vs thin wrapper pinned by test). The plan does
   set a default ("Prefer reuse"), gate the alternative on a tolerance, and
   require recording the choice in the Decision Log — acceptable for an
   execplan, but the planner could pre-commit to the promotion to remove the
   in-flight decision. Note that `_desloppify` chose NOT to reuse this helper
   (it wrote its own `_chapter_text`); the plan's stronger "literally the same
   function" constraint is a deliberate tightening, which is fine, but the
   reviewer should expect the promotion to touch `disk_evidence.py`'s one
   internal caller and the `state/__init__.py` surface + `__all__`.

2. Temp-file prefix cosmetic mismatch: `write_text_atomically` reuses
   `_TEMP_PREFIX = ".state.toml."`, so the `compiled.md` temp file is named
   `.state.toml.XXXX.tmp` inside `manuscript/`. Functionally harmless (same
   directory, atomic rename), and the Work item 1 leaked-temp assertion still
   works, but the name is misleading. Consider a neutral prefix (e.g.
   `.compiled.md.`) or a shared generic prefix when the writer is generalized.
   Not load-bearing.

3. The plan asserts `len(rendered.encode("utf-8"))` for the `bytes` field. This
   is correct (str→utf-8 byte length), and the snapshot redaction keeps the
   `compiled` path working-relative. Confirm the snapshot's `bytes`/`chapters`
   are semantically asserted (the plan says so — AGENTS.md snapshot rule).

4. Scaling (Buzzy Bee): the result payload is bounded (path + 2 ints) and the
   compile is O(total draft bytes) with a single join — no per-chapter envelope
   growth. Fine for the design's chapter-count range. The whole-manuscript read
   holds every draft body in memory simultaneously (`_present_draft_bodies`
   returns a `list[str]`), identical to the existing disk-evidence detector, so
   no new scaling concern is introduced.

## Pre-mortem (Doggylump)

- Most likely failure: a freshly compiled tree fails `novel-state check` because
  the write path and the invariant disagree on separator/read-rule/order.
  Blast radius: every compile. Mitigation already in the plan: the round-trip
  oracle test (Work item 2) and the literal-same-function read rule. Adequate.
- Second failure: an undecodable `draft.md` escapes as exit 1 instead of 3.
  Mitigated by the `STATE_INPUT_ERRORS` wrapper and an explicit undecodable-draft
  test. Adequate; precedented by `_recount`/`_desloppify`.
- Third failure: non-deterministic ordering from a glob. Mitigated by ordering
  strictly via `sorted(state.chapters, key=…number)` plus an out-of-order-on-disk
  test. Adequate.

## Alternatives checkpoint (Wafflecat)

The strongest alternative is to put the compile body and the text-writer in a
single new module rather than splitting the writer into `state/document.py`. The
plan's split is correct: it keeps the atomic-write discipline single-homed
(D-WRITER) and re-exported, matching how every other mutator reaches
`write_document_atomically`. No credible structural alternative improves on the
chosen decomposition; the design space here is genuinely narrow because the
invariant oracle and the production join rule already exist. That narrowness is
itself a signal the design is on solid ground.
