# Implement `recount` as a pure aggregation over chapter drafts

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DONE

## Purpose / big picture

Today the harness's word counts are hand-typed. The agent edits
`[word_counts].current` and `[word_counts].by_chapter` in `state.toml` by hand,
and the design (`docs/novel-ralph-harness-design.md` §4.1) names this as a
source of drift the field report repeatedly tripped over. This task delivers the
`novel-state recount` mutator: a single command that re-derives both fields by
a pure aggregation over the on-disk chapter drafts and writes the validated
result, so a human never types a word count again.

After this change a user can run, from a project's process directory:

```console
$ novel-state recount
{"command": "novel-state recount", "ok": true, "result": {"current": 8}}
```

and observe `working/state.toml`'s `[word_counts].current` and
`[word_counts].by_chapter` rewritten to match what is actually on disk under
`working/manuscript/chapter-NN/draft.md`, with the per-chapter values summing
to the total. Two consecutive runs over unchanged drafts produce a
byte-for-byte identical `state.toml` (idempotence), and the command refuses
with exit `3` (writing nothing) when the state is missing, unparseable,
structurally incomplete, or when the recount would produce an incoherent state.

You can see it working through the new behavioural scenario
`tests/features/recount.feature` (a recount over a tree with two drafted
chapters writes the summed counts and is idempotent on a second run) and the
machine-mode envelope snapshot, both described under "Validation and
acceptance".

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **Word-count algorithm is fixed and shared with the existing oracle.** A
  chapter's word count is `len(draft_text.split())` over the UTF-8 body of
  `working/manuscript/chapter-NN/draft.md` — the whitespace-split token count.
  This is the exact algorithm the live-draft cross-check oracle already pins in
  `tests/working_corpus/_live_draft.py:69-92` (`live_draft_counts`) and that
  the corpus body generator `tests/working_corpus/_specs.py:205-214`
  (`draft_body`) is built to satisfy. Production `recount` must agree with this
  oracle byte-for-byte in its counting, or the §1.3.2 corpus and the §5.2
  `gate-ratio-consistent` numerator (`sum(by_chapter.values())`) would disagree
  with what `recount` writes. Do not invent a second counting rule (no
  paragraph/sentence/character variant, no Markdown stripping).
- **`by_chapter` keys are the zero-padded two-digit chapter string.** Keys are
  `f"{number:02d}"` (`"01"`, `"02"`, …), matching
  `tests/working_corpus/_specs.py:195-202` (`by_chapter_key`) and
  `skill/novel-ralph/references/state-layout.md:115`. Chapter directories are
  `chapter-NN` zero-padded (`_specs.py:186-192`; state-layout.md:54-56).
- **`current` equals `sum(by_chapter.values())`.** This is design §5.2 invariant
  3 (`by-chapter-sum`), pinned by `derive_current`
  (`tests/working_corpus/_specs.py:264-274`). `recount` must write the two
  fields so this holds, then validate the proposed state and refuse (exit `3`)
  if any §5.2 invariant is breached, leaving the prior `state.toml` intact.
- **Validate before persist; refuse with exit `3` and write nothing.** Every
  mutator validates the *proposed* state with `validate_state` before writing
  and, on a non-empty verdict or any load/parse fault, raises `StateInputError`
  (exit `3`, the state-error channel — ADR-003; design §3.2), leaving
  `state.toml` byte-for-byte intact. This is the established mutator contract in
  `novel_ralph_skill/commands/_state_mutators.py` (`_refuse_if_incoherent`,
  `_load_document_or_state_error`, `_state_view_or_state_error`). A *refused*
  recount must not be mistaken for the benign exit `1` the loop continues on.
- **Lossless `tomlkit` round-trip and atomic single-file write.** `recount`
  loads through `load_document` (`tomlkit`, not `tomllib`), edits the live
  `TOMLDocument` in place, and writes through `write_document_atomically`
  (temp-file-plus-`Path.replace`), preserving hand-authored comments and layout
  (ADR-002; design §5.3, §3.4). It must not re-serialize from the typed `State`
  read view.
- **Success `result` is write-shaped, never `check`'s read shape.** `recount`'s
  success `result` names what it changed (the counts it wrote), and never
  echoes the `check` query's `violations` key (design §3.3;
  `docs/developers-guide.md:438-449`; `docs/issues/audit-2.2.2.md` Finding 2).
- **The command shells out to nothing — no cuprum surface is added.** `recount`
  is pure Python file I/O over `pathlib` plus `tomlkit`; design §2 lines 256
  and 725 record that v1 commands shell out to nothing, so the cuprum catalogue
  boundary is not exercised. Adding a cuprum/subprocess execution path here is
  out of scope and would be a tolerance breach (see Tolerances → Dependencies).
- **`recount` writes a single file, so it opens no `[pending_turn]` bracket.**
  It rewrites only `working/state.toml`, already atomic via `Path.replace`,
  exactly like `set-cursor` and `advance-phase`. The `[pending_turn]` producer
  bracket is for *genuinely multi-file* writes; `recount` does not use it
  (design §4.1 line 271 — `recount` re-derives only `[word_counts]`; design
  §3.4 lines 240-241, where "a recount" is named as *one write among several in
  a turn*, not the command writing several files). See Decision Log D-PT. **
  `docs/developers-guide.md` mis-lists `recount` as multi-file in *two* places,
  and this plan corrects *both* as part of Work item 3 step 5:** (a) **lines
  467-468** — "that belongs to the genuinely multi-file mutators (`recount`,
  `reconcile`)"; and (b) **lines 202-206** — the "Checker/mutator segregation"
  paragraph, which lumps `init`/`set-cursor`/`advance-phase`/`recount` together
  with `reconcile` and `novel-compile` and says they are "bracketed by a
  `[pending_turn]` intent record so a torn multi-file turn is recoverable".
  Both passages contradict §4.1/§3.4 and the single-file reality of `recount`
  (and of `init`/`set-cursor`/`advance-phase`); correcting only one would leave
  the source-of-truth doc self-contradictory (Round-2 blocking point A).
- **No file in `working/` is read for content other than `draft.md`.** `recount`
  does not read `done.flag`, `compiled.md`, or any other artefact — that is
  task 2.3.2's disk-authoritative reconciliation, deliberately out of scope
  here.
- **en-GB Oxford spelling** (`-ize`/`-yse`/`-our`) in all prose, comments, and
  commit messages (AGENTS.md; the en-gb-oxendict convention), with the standard
  carve-out for external API names.
- **400-line module cap** per file (AGENTS.md "Keep file size manageable").

## Tolerances (exception triggers)

Stop and escalate (do not work around) when any threshold is reached:

- **Scope:** if the production change to `_state_mutators.py` plus a new
  word-count helper module exceeds ~250 net new lines, or touches more than 4
  non-test files, stop and escalate.
- **Interface:** if `build_app`'s existing subcommand signatures or
  `CommandOutcome`/`StateInputError`/`ExitCode` must change to add `recount`,
  stop and escalate. (Adding a new `recount` subcommand is in scope; mutating
  existing public signatures is not.)
- **Dependencies:** if any new external dependency (including any cuprum
  execution path or subprocess call) appears necessary, stop and escalate — the
  Constraints forbid it.
- **Algorithm divergence:** if the production count cannot be made to agree with
  `tests/working_corpus/_live_draft.py:live_draft_counts` for any corpus tree,
  stop and escalate rather than introducing a second counting rule.
- **Iterations:** if `make all` still fails after 3 fix attempts on a single
  work item, stop and escalate.
- **Ambiguity:** if a §5.2 invariant interaction makes the
  "key `by_chapter` by manifest vs. by present drafts" decision (Decision Log
  D-KEY) materially change behaviour beyond what its test pins, stop and
  present options.

## Risks

- Risk: production `recount` and the corpus oracle drift apart on the counting
  rule (e.g. one strips Markdown, the other does not), so the §1.3.2 corpus and
  the real command disagree. Severity: high Likelihood: low Mitigation: extract
  the count into one small helper and pin it equal to `live_draft_counts` with
  a property test over generated draft bodies (Work item 1); the `draft_body`
  generator and the oracle already agree, so the helper has a ready oracle.

- Risk: `by_chapter` includes or omits zero-count chapters inconsistently with
  the manifest, so `recount` produces a state whose `by_chapter` keys are not
  in bijection with `[chapters]`, surprising a later `check`. Severity: medium
  Likelihood: medium Mitigation: pin the key set to the chapter manifest
  (Decision Log D-KEY) and test the absent-`draft.md` and empty-`draft.md`
  cases explicitly (Work item 2).

- Risk: a non-idempotent write (e.g. dict ordering churn in the `by_chapter`
  inline table) breaks the roadmap idempotence success criterion. Severity:
  medium Likelihood: low Mitigation: write `by_chapter` in ascending
  zero-padded key order and assert byte-for-byte stability of a second run in
  both a unit test and the BDD scenario (Work items 2 and 3).

- Risk: a `draft.md` that is not valid UTF-8 (or otherwise unreadable —
  permission denied, a directory where a file is expected) raises an exception
  that, if not routed to the exit-`3` channel, escapes as exit `1`. Severity:
  medium Likelihood: low Mitigation: `recount_words` catches **only**
  `FileNotFoundError` per chapter (an absent `draft.md` contributes `0`, per
  D-KEY) and lets every other `OSError` (`PermissionError`,
  `IsADirectoryError`) and `UnicodeDecodeError` propagate. The `recount` body
  re-raises these as `StateInputError` under the existing `STATE_INPUT_ERRORS`
  tuple, so they reach exit `3`. Tested with an undecodable draft (Work item
  2). Note: this plan does **not** parse a directory *name* suffix anywhere —
  every chapter path is built from a manifest integer via
  `f"chapter-{number:02d}"` (D-KEY) — so there is no "malformed `chapter-NN`
  suffix" code path to guard, and no such test exists (this corrects a vacuous
  Round-1 risk/test; see Round-1 blocking point 2).

- Risk: `recount` legitimately refuses (exit `3`, writes nothing) on a state
  that previously passed `check`. Re-deriving `by_chapter` from disk changes
  `drafted_total`, which feeds the §5.2 `GATE_RATIO_CONSISTENT` and
  `CONSECUTIVE_CLEAN_WITHIN_DRAFTED` invariants; a state whose hand-typed
  counts satisfied those gates may breach them once recounted. Severity: low
  Likelihood: medium Mitigation: this is correct behaviour under the
  validate-before-persist contract (Constraints), not a bug — but it is an
  operator-facing failure mode. Work item 2 adds a unit test that a tree whose
  recounted `by_chapter` breaches a §5.2 invariant refuses with exit `3` and
  leaves `state.toml` byte-for-byte intact, and the refusal message must name
  the breached invariant clearly via
  `_refuse_if_incoherent(proposed, context="recount")` (Round-1 advisory).

## Progress

- [x] Work item 1 — Extract and pin the shared word-count aggregation helper.
- [x] Work item 2 — Implement the `recount` mutator body and unit/property
      tests.
- [x] Work item 3 — Register `recount`, add the BDD scenario and envelope
  snapshot, and update the guides.

Work item 1 progress (2026-06-24): `recount_words` landed in
`novel_ralph_skill/state/wordcount.py` and is re-exported from the `state`
package. The unit + property tests in `tests/test_state_wordcount.py` pass;
red-before-green was confirmed by temporarily replacing `len(text.split())`
with `len(text.splitlines())` (the property and the example test both went red,
then reverted). `make all` green at HEAD; one coderabbit run returned two
trivial findings — added assertion messages to the unit tests, and kept the
`cabc.Mapping` return annotation (the plan's pinned signature; the read-only
view is intentional and the caller copies via `dict(...)`). Surprise: the
property test's per-example `tmp_path` subdirectory must be *globally* unique (a
`uuid4` suffix), because `live_draft_counts` globs *every* present draft, so a
name collision across examples mixed cases — the property correctly caught this
before the production code was ever wrong. Committed as eddc7ef.

Work item 2 progress (2026-06-24): the `recount` body landed. **Deviation from
the plan (justified):** the plan put `recount` in `_state_mutators.py`, but
adding the body there pushed that file to 441 lines, breaching the 400-line cap
(a Constraint). The body therefore lives in a new
`novel_ralph_skill/commands/_recount.py` module that reuses the shared
load/refuse helpers (`_state_path`, `_working_dir`,
`_load_document_or_state_error`, `_state_view_or_state_error`,
`_refuse_if_incoherent`) from `_state_mutators.py`; both modules now sit under
the cap (321 and 154 lines). The `_working_dir()` resolver was added beside
`_state_path()`. **`recount` was also registered in `build_app` in this work
item** (the plan scheduled registration for WI3 step 1), because WI2's
violations-ownership extension drives `recount` through the app and so needs it
registered. The fault routing uses a `_recount_or_state_error` wrapper mirroring
`_load_document_or_state_error`. `make all` green at HEAD (352 passed);
red-before-green confirmed by mutating the `current` write to `current + 1`
(three tests went red, then reverted). One coderabbit run returned two findings,
both skipped with reason: (a) a "major" 80-column wrap finding against
`roadmap-2-3-1.review-r1.md` — a planning-phase review artefact this task did not
author and does not edit; (b) a "trivial" architectural-dependency finding on
importing `STATE_INPUT_ERRORS` from `novel_state` — this is the *established*
pattern (`_state_mutators.py` already imports it the same way), so following it
keeps the codebase consistent; relocating the constant to a contract module
would touch the public `novel_state`/`_state_mutators` surface and the corpus
parse-error pin, an out-of-scope refactor (Interface tolerance). Committed as
f202dd8.

Work item 3 progress (2026-06-24): the BDD scenario
(`tests/features/recount.feature` + `tests/steps/recount_steps.py` +
`tests/test_recount_bdd.py`), the `recount` success-envelope snapshot, and the
two guide corrections landed. Registration was already done in WI2, so WI3
step 1 was a no-op. **Deviation (justified):** the plan suggested putting the e2e
reachability check in `test_console_scripts_e2e.py` or `test_novel_state_check.py`;
adding it to the latter pushed that file to 416 lines (over the 400-line cap), so
the fast entry-point reachability test lives in a new `tests/test_recount_e2e.py`
instead. Both developers'-guide mis-listings (the "Checker/mutator segregation"
paragraph and the single-file-write paragraph) were corrected and a grep for
`recount` confirmed no remaining sentence implies it is multi-file or bracketed.
`make all` green (355 passed); `make markdownlint` and `make nixie` pass over the
two edited guides (no Mermaid added). One coderabbit run returned a single
trivial finding — added `slots=True` to the private `_Outcome` step dataclass —
applied; `make all` stayed green. Committed as 18b4e3b.

## Surprises & discoveries

- Observation: the word-count algorithm `recount` needs is already pinned by the
  test oracle, not just the design prose. Evidence:
  `tests/working_corpus/_live_draft.py:69-92` (`live_draft_counts`) globs
  `manuscript/chapter-*/draft.md`, reads UTF-8, and takes `len(text.split())`;
  `tests/working_corpus/_specs.py:205-214` (`draft_body`) generates bodies whose
  `split()` count is exactly the intended word count. Impact: removes the
  central design fork — there is one verified counting rule, and the helper can
  be pinned equal to it rather than guessed.

- Observation: `recount` writes only `state.toml`, yet
  `docs/developers-guide.md`
  mis-lists it among the "genuinely multi-file mutators" in *two* places.
  Evidence: design §4.1 line 271 ("Re-derive `word_counts.current` and
  `by_chapter`") names only `state.toml` fields; design §3.4 lines 240-241 name
  "a recount" as *one write among several in a turn*, not the command writing
  several files. `docs/developers-guide.md:465-468` reserves the
  `[pending_turn]` bracket for "genuinely multi-file" writes but then
  erroneously includes `recount` in that list (lines 467-468). Separately, the
  "Checker/mutator segregation" paragraph at lines 202-206 lumps `init`/
  `set-cursor`/`advance-phase`/`recount` in with `reconcile`/ `novel-compile`
  and claims they are all "bracketed by a `[pending_turn]` intent record so a
  torn multi-file turn is recoverable". Impact: `recount` follows the
  `set-cursor`/`advance-phase` single-file pattern (no `[pending_turn]`), not
  the bracketed pattern. Pinned in Decision Log D-PT. *Both* guide passages
  (467-468 and 202-206) are documentation defects this plan corrects in Work
  item 3 step 5 (Round-1 blocking point 1; Round-2 blocking point A).

## Decision log

- Decision (D-KEY): `recount` keys `by_chapter` by the **chapter manifest**
  (`state.chapters`), emitting one entry per manifest chapter — `0` for a
  chapter whose `draft.md` is absent or empty. Rationale: design §5.2 invariant
  5 makes the manifest the authoritative chapter set and requires
  manifest-to-disk bijection; keying `by_chapter` by the manifest keeps the
  recounted table in step with that set and gives a stable, deterministic key
  order. The alternative (key only by present non-empty drafts) would silently
  drop chapters from `by_chapter` and is rejected. `current` is
  `sum(by_chapter.values())` either way, so §5.2 invariant 3 holds. The chapter
  number drives both the directory name (`chapter-NN`) and the key (`NN`).
  Date/Author: 2026-06-24, planning agent.

- Decision (D-PT): `recount` performs a single atomic `state.toml` write and
  opens no `[pending_turn]` bracket. Rationale: it rewrites one file, already
  atomic via `Path.replace`, exactly like the existing single-file mutators;
  the §3.4 bracket exists for multi-file turns. Design §4.1 line 271 says
  `recount` re-derives only `[word_counts]` (one file), and §3.4 lines 240-241
  use "a recount" as an example of *one write among several in a turn*, not the
  command itself writing several files — so the command is single-file. Using
  the bracket here would be ceremony with no torn-turn to protect against.
  `docs/developers-guide.md` states the opposite in *two* places — lines
  467-468 (lists `recount` as multi-file) and lines 202-206 (the
  "Checker/mutator segregation" paragraph, which brackets `init`/`set-cursor`/
  `advance-phase`/`recount` along with the genuinely multi-file writers); both
  are documentation defects and Work item 3 step 5 corrects *both* to agree
  with this decision (Round-1 blocking point 1; Round-2 blocking point A). The
  plan's reading was confirmed substantively correct by the Round-1 and Round-2
  reviews. Date/Author: 2026-06-24, planning agent.

- Decision (D-PT-DESIGN): the design's §3.4 line 242 loose phrasing ("each
  mutator opens a `[pending_turn]` intent record … *before* it touches any
  other file") is **not** treated as contradicting D-PT, and the design is
  **not** edited by this task. Rationale: §3.4:242 reads in isolation as if
  *every* mutator brackets, but §4.1 (line 271, `recount` re-derives only
  `[word_counts]`) and the §3.4 framing of "a recount" as one write among
  several in a turn (lines 240-241) make the single-file reading authoritative;
  the more specific passage governs. The design tension predates this plan, the
  plan correctly sides with §4.1, and editing the design is out of scope here
  (only the developers' guide, which the source-of-truth design should drive,
  is corrected). Recorded so a future reader does not treat §3.4:242 as a
  contradiction of D-PT (Round-2 advisory). Date/Author: 2026-06-24, planning
  agent.

- Decision (D-CUPRUM): no cuprum API is pinned or used.
  Rationale: `recount` is pure file I/O over `pathlib`+`tomlkit`; design §2
  lines 256 and 725 state v1 commands shell out to nothing. The locked cuprum
  (`0.1.0`, `uv.lock`) catalogue/`Program`/`sh` surface is therefore not
  exercised by this task. Recorded so a reviewer does not expect a cuprum
  citation. Date/Author: 2026-06-24, planning agent.

- Decision (D-CURRENT): `recount` defines `current` as the **drafted sum**
  (`sum(by_chapter.values())`), and defers any `compiled.md`-versus-drafts
  reconciliation to task 2.3.2. Rationale:
  `skill/novel-ralph/references/state-layout.md:114` and the schema describe
  `current` as "words in compiled.md (or sum of drafts)"; when a `compiled.md`
  exists its token count can diverge from `sum(by_chapter)` (separator joins
  between chapters). `recount` is deliberately scoped to read only `draft.md`
  (Constraints), so it writes `current = sum(by_chapter)` and satisfies §5.2
  invariant 3 by construction. This is not a bug: the compiled-versus-drafts
  reconciliation is roadmap task 2.3.2 (`reconcile` / §5.4). Recorded so a
  reviewer does not read the drafts-only `current` as a defect (Round-1
  advisory). Date/Author: 2026-06-24, planning agent.

- Decision (D-CWD): the new unit, property, and BDD tests must
  `monkeypatch.chdir(working.parent)` (BDD: `chdir` into the prepared tree's
  parent) before invoking `recount`. Rationale: `recount` resolves a
  **cwd-relative** `_state_path()` (`working/state.toml`), exactly like
  `set-cursor` and `advance-phase`. The existing `set-cursor` property test is
  emphatic that the chdir must precede the call
  (`tests/test_state_mutators_unit.py:200-208`). The new tests inherit this
  requirement; calling it out here prevents a flaky "state.toml not found"
  failure that would look like a `recount` bug (Round-1 advisory). Date/Author:
  2026-06-24, planning agent.

- Decision (D-LOC): the count helper lives in a new module
  `novel_ralph_skill/state/wordcount.py` (re-exported from
  `novel_ralph_skill/state/__init__.py`), not inside `_state_mutators.py`.
  Rationale: the count is a reusable pure function the later `wordcount`
  command (roadmap §4.5) and task 2.3.2's reconciliation will both want;
  placing it in the `state` package keeps it next to the schema it serves and
  away from the command layer, and avoids pushing `_state_mutators.py` toward
  the 400-line cap. Date/Author: 2026-06-24, planning agent.

## Context and orientation

This repository is the `novel-ralph` harness: a set of Cyclopts console
commands that manage a novel-in-progress under `working/`. The relevant slice
is the `novel-state` command and the typed `state` package.

Key files (full repository-relative paths):

- `docs/novel-ralph-harness-design.md` — the design. §4.1 (the `novel-state`
  subcommand table; `recount` row at line 271 and the
  eliminate-hand-typed-counts paragraph at lines 275-282), §5.1 (schema), §5.2
  (invariants; invariant 3 `by-chapter-sum` at line 453, invariant 5 manifest
  bijection at lines 460-465), §5.3 (`tomlkit` round-trip), §3.2 (exit codes),
  §3.4 (atomic / `[pending_turn]`).
- `docs/adr-002-toml-round-trip-tomlkit.md` — lossless round-trip rationale.
- `docs/adr-003-*` — exit-code contract (exit `3` for state/input error).
- `docs/developers-guide.md` — mutator conventions (write-shaped `result`, the
  two-helper load path) at lines 438-468.
- `docs/users-guide.md` — user-facing command list (lines 86-113).
- `skill/novel-ralph/references/state-layout.md` — the authoritative on-disk
  layout: `chapter-NN/draft.md` (lines 37-56), `[word_counts]` table (lines
  111-116, `by_chapter` keyed by zero-padded two-digit string at line 115).
- `novel_ralph_skill/commands/novel_state.py` — the `novel-state` Cyclopts app
  (`build_app`), the `check`/`init` bodies, `WORKING_DIR_NAME`,
  `STATE_INPUT_ERRORS`, and `_load_or_state_error`.
- `novel_ralph_skill/commands/_state_mutators.py` — the `set-cursor` and
  `advance-phase` mutator bodies plus the shared load/refuse helpers
  (`_state_path`, `_load_document_or_state_error`, `_state_view_or_state_error`,
  `_refuse_if_incoherent`). `recount`'s body lands here.
- `novel_ralph_skill/state/schema.py` — the frozen `State`/`WordCounts`/
  `ChapterEntry` dataclasses. `WordCounts.by_chapter` is keyed by the
  zero-padded two-digit string (lines 228-261).
- `novel_ralph_skill/state/document.py` — `load_document`,
  `document_to_state`, `write_document_atomically` (the writer seam every
  mutator uses).
- `novel_ralph_skill/state/validate.py` — `validate_state` and the §5.2
  invariant names (`BY_CHAPTER_SUM` at line 47).
- `novel_ralph_skill/state/__init__.py` — the `state` package's public surface.
- `tests/working_corpus/_live_draft.py` — `live_draft_counts` (the existing
  word-count oracle, lines 69-92).
- `tests/working_corpus/_specs.py` — `chapter_dir_name`, `by_chapter_key`,
  `draft_body`, `derive_by_chapter`, `derive_current` (lines 186-274) and the
  `WorkingTreeSpec` dataclass.
- `tests/conftest.py` — the `WorkingTreeSpec` carve-out import and the working-
  tree fixtures used by mutator BDD/snapshot tests.
- `tests/test_state_mutators_unit.py`,
  `tests/test_novel_state_mutator_snapshots.py`,
  `tests/features/advance_phase_refusal.feature`,
  `tests/steps/advance_phase_steps.py` — the patterns the new tests mirror.

Definitions:

- **Mutator**: a `novel-state` subcommand that writes state, as opposed to a
  *checker* (read-only). `recount` is a mutator (design §4.1).
- **Word count of a chapter**: `len(draft_text.split())` over the UTF-8 body of
  that chapter's `draft.md` — the whitespace-split token count (Constraints).
- **`by_chapter`**: `[word_counts].by_chapter`, a TOML inline table keyed by the
  zero-padded two-digit chapter string, value the chapter's word count.
- **Exit `3`**: the state/input-error exit code (ADR-003; design §3.2), raised
  by
  `StateInputError`; distinct from the benign `1` the harness loops on.

## Plan of work

Three ordered, independently committable, gate-passable work items. Each ends
with `make all` green (plus `make markdownlint` and `make nixie` for the
markdown work in Work item 3).

### Work item 1 — Extract and pin the shared word-count aggregation helper

Goal: one pure function that maps a `working/` directory (or a chapter manifest
plus that directory) to the recounted `(current, by_chapter)`, pinned equal to
the existing oracle so production and corpus cannot drift.

Documentation to read first: design §4.1 (lines 271-282), §5.2 (invariant 3,
line 453; invariant 5, lines 460-465);
`skill/novel-ralph/references/state-layout.md` lines 37-56 and 111-116;
`tests/working_corpus/_live_draft.py:69-92`;
`tests/working_corpus/_specs.py:186-274`.

Skills to load: `python-router` → `python-data-shapes` (the return shape) and
`python-iterators-and-generators` (the aggregation); then `python-verification`
to confirm the adversary, then `hypothesis` (a concrete oracle —
`live_draft_counts` — exists, so Hypothesis is the right property tool, not
CrossHair). Use `leta` for navigation
(`leta show novel_ralph_skill.state.schema.WordCounts`,
`leta refs live_draft_counts`) and `sem` for history if needed.

Edits:

1. Create `novel_ralph_skill/state/wordcount.py` defining a pure function
   `recount_words` (the full signature is pinned in "Signatures that must exist"
   below), that for each manifest chapter reads
   `working_dir / "manuscript" / f"chapter-{number:02d}" / "draft.md"`, counts
   `len(text.split())`, and returns the total and an ordered `by_chapter`
   mapping keyed by `f"{number:02d}"`. Keep it under the 400-line cap (it will
   be ~60 lines with docstrings). The function reads only `draft.md`
   (Constraints) and keys by the manifest (Decision Log D-KEY). **Fault
   boundary (Round-1 blocking point 3 — implement exactly this):** wrap each
   per-chapter read in a narrow try/except:

   ```python
   try:
       text = path.read_text(encoding="utf-8")
   except FileNotFoundError:
       count = 0
   ```

   Catch **only** `FileNotFoundError` and treat it as `0` (an undrafted
   chapter contributes nothing — D-KEY). Do **not** catch a broad `OSError` and
   do **not** catch `UnicodeDecodeError`: a `PermissionError`, an
   `IsADirectoryError`, or an undecodable body must propagate out of
   `recount_words` unchanged, so the `recount` body can route them to exit `3`
   (Work item 2 step 2). A broad `except OSError` here would (a) turn an absent
   draft into exit `3`, breaking D-KEY, and (b) silently swallow
   `PermissionError`/`IsADirectoryError` as `0` — both wrong. The helper itself
   raises no `StateInputError`; it stays a pure I/O function and lets the
   command layer own the exit-code translation.
2. Re-export the helper from `novel_ralph_skill/state/__init__.py`
   (`from ... .wordcount import recount_words`, add to `__all__`).

Tests to add (AGENTS.md "unit and behavioural tests … property tests … over a
range of inputs"):

- `tests/test_state_wordcount.py` (unit): a tree with two non-empty drafts and
  one empty draft returns `current == sum` and `by_chapter` with the empty
  chapter at `0`; an **absent** `draft.md` (manifest chapter with no file)
  contributes `0` and does **not** raise (pins `FileNotFoundError`-as-`0`,
  Round-1 blocking point 3); the key form is the zero-padded string. Add a
  negative case at the helper level: an **undecodable** `draft.md` (non-UTF-8
  bytes) raises `UnicodeDecodeError` *out of `recount_words`* (the helper does
  not swallow it; the command layer translates it to exit `3` — Work item 2).
  Build trees with the corpus helpers (`chapter_dir_name`, `draft_body`) so the
  expected counts are exact.
- `tests/test_state_wordcount.py` (property, Hypothesis): over a manifest of
  generated chapter numbers and per-chapter word counts materialized with
  `draft_body`, `recount_words(working_dir, manifest)` agrees with
  `live_draft_counts(working_dir)` on the total, and
  `sum(by_chapter.values()) == current`. This pins the production helper equal
  to the oracle (Risk "production and oracle drift"). Use `@settings` mirroring
  the existing `test_state_mutators_unit.py` style; suppress
  `function_scoped_fixture` health-checks if a `tmp_path`-style fixture is
  involved, as that suite does. **Scope of the oracle (Round-2 advisory).**
  `live_draft_counts` (`_live_draft.py:86-92`) **globs** the present `draft.md`
  files and returns a *total* only — it exposes no per-chapter map — whereas
  `recount_words` iterates the **manifest** (absent draft → `0`). The two agree
  on the **total** (an absent draft contributes `0` in both), so the property
  is correctly scoped to the total. The per-chapter `by_chapter` *mapping* is
  therefore pinned by the **example-based unit test** above (which builds exact
  expected entries with `by_chapter_key`/`draft_body`), not by the oracle.
  State this split in the test docstring so a reader does not expect
  `live_draft_counts` to cover key-level agreement.

Validation: `make all` green; the new property test fails if the helper
diverges from `live_draft_counts` (verify by temporarily breaking the count,
e.g. `len(text.splitlines())`, and seeing red, then reverting).

Acceptance: `recount_words` exists, is re-exported, and the property test passes
(`tests/test_state_wordcount.py::...agrees_with_live_oracle`).

### Work item 2 — Implement the `recount` mutator body with unit/property tests

Goal: the `recount` body that loads the document, recounts, rewrites the two
`[word_counts]` fields in place, validates the proposed state, and writes
atomically — refusing with exit `3` on any fault.

Documentation to read first: `docs/developers-guide.md:438-468` (write-shaped
`result`, the two-helper load path, single-file-no-bracket); design §3.2, §3.4,
§5.2; `novel_ralph_skill/commands/_state_mutators.py` in full (mirror
`set_cursor`/`advance_phase`).

Skills to load: `python-router` → `python-errors-and-logging` (narrow `except`,
`raise … from`, the exit-`3` channel) and `python-types-and-apis` (the
`CommandOutcome` signature); `python-verification` then `hypothesis` for the
accept-iff-coherent property; `leta` for navigation.

Edits in `novel_ralph_skill/commands/_state_mutators.py`:

1. Add `recount() -> CommandOutcome`. It calls `_state_path()`,
   `_load_document_or_state_error(path)`, then
   `_state_view_or_state_error( document)` to prove structural completeness and
   obtain the manifest (`prior.chapters`). It computes `(current, by_chapter)`
   via `recount_words(_working_dir(), prior.chapters)` — resolve the working
   directory from the same `WORKING_DIR_NAME` root `_state_path()` uses (add a
   tiny `_manuscript_root()`/reuse `_state_path().parent`). It edits
   `document["word_counts"]["current"]` and rebuilds
   `document["word_counts"]["by_chapter"]` as a fresh `tomlkit` inline table in
   ascending key order (idempotence; Risk "non-idempotent write"). It then
   derives the proposed view (`_state_view_or_state_error`), calls
   `_refuse_if_incoherent(proposed, context="recount")`, writes atomically, and
   returns a write-shaped `CommandOutcome`:

   ```python
   CommandOutcome(
       code=SUCCESS,
       result={"current": current, "by_chapter": dict(by_chapter)},
       messages=[...],
   )
   ```

   No `violations` key (Constraints).
2. **Fault routing (Round-1 blocking point 3).** `recount_words` has already
   absorbed the only benign case — an absent `draft.md` returns `0` (it catches
   `FileNotFoundError` narrowly per chapter; Work item 1 step 1). The `recount`
   body therefore catches the *propagating* read faults — `UnicodeDecodeError`
   (an undecodable body; a `ValueError` subclass), `PermissionError`,
   `IsADirectoryError`, and any other non-`FileNotFoundError` `OSError` — by
   wrapping the `recount_words(...)` call in
   `except STATE_INPUT_ERRORS as exc: raise StateInputError(...) from exc`,
   mirroring `_load_document_or_state_error` in the same module
   (`_state_mutators.py:88`). Because those exceptions are all members of
   `STATE_INPUT_ERRORS` (`OSError`, `ValueError` — verified in
   `novel_ralph_skill/commands/novel_state.py:85-91`: the tuple is
   `(OSError, TOMLDecodeError, KeyError, ValueError, TypeError)`), this single
   wrap routes them to exit `3` with a clear message and cannot escape to exit
   `1`. Do **not** add a manifest-suffix-parse guard: there is no
   directory-name parsing in this design (every path comes from a manifest
   integer — D-KEY), so the only fault classes reaching this boundary are the
   file-read ones above.

Tests to add:

- `tests/test_state_mutators_unit.py` (extend) or a new
  `tests/test_recount_unit.py`: `recount` over a two-chapter tree writes the
  summed `current` and the per-chapter table, returns exit `0` with a
  write-shaped `result` (no `violations`); a second invocation leaves
  `state.toml` byte-for-byte identical (idempotence unit assertion); a missing
  `state.toml`, an incomplete `state.toml`, and an **undecodable** `draft.md`
  (write non-UTF-8 bytes, e.g. `b"\xff\xfe"`, to a chapter's `draft.md`) each
  raise `StateInputError` (exit `3`) and leave the prior file intact. Add a
  positive companion that an **absent** `draft.md` (its chapter directory
  present but the file removed) succeeds with that chapter at `0` — this pins
  the `FileNotFoundError`-as-`0` versus `UnicodeDecodeError`-as-exit-`3`
  boundary (Round-1 blocking point 3) on opposite sides of the line. Do **not**
  write a "malformed `chapter-NN` directory" test — no directory-name suffix is
  ever parsed under D-KEY, so such a test is vacuous (Round-1 blocking point
  2). Each refusal test must `monkeypatch.chdir(working.parent)` before calling
  `recount`, mirroring `tests/test_state_mutators_unit.py:200-208` (the
  cwd-relative `_state_path()`; see Decision Log D-CWD).
- A `recount`-legitimately-refuses test: build a tree whose hand-typed counts
  pass `check` but whose disk-derived `by_chapter` breaches a §5.2 gate
  invariant (`GATE_RATIO_CONSISTENT` or `CONSECUTIVE_CLEAN_WITHIN_DRAFTED`);
  assert exit `3`, a refusal message naming the breached invariant, and
  `state.toml` byte-for-byte unchanged (Risk "recount legitimately refuses";
  Round-1 advisory).
- Property (Hypothesis): over generated per-chapter word counts against a fixed
  populated manifest, `recount` succeeds and the written
  `sum(by_chapter.values()) == current`, and the written state passes
  `validate_state` (accept-iff-coherent, mirroring the existing `set-cursor`
  property in `test_state_mutators_unit.py`). The property test, like the unit
  tests, must `monkeypatch.chdir(working.parent)` before each `recount` call
  (Decision Log D-CWD).
- `tests/test_novel_state_violations_ownership.py` (extend): assert `recount`'s
  success `result` carries no `violations` key — the cross-subcommand pin that
  `violations` belongs to `check` alone (developers-guide.md:448-449).

Validation: `make all` green. Confirm exit-`3` refusals write nothing by
asserting the prior bytes are unchanged (the pattern in the advance-phase BDD
steps).

Acceptance: the `recount` body exists, all new unit/property tests pass, and
the ownership test pins `violations` to `check`.

### Work item 3 — Register `recount`, add the BDD scenario, snapshot, and guides

Goal: wire `recount` into the Cyclopts app, prove the end-to-end behaviour and
the roadmap success criteria with a behavioural scenario and a machine-mode
envelope snapshot, and document the command.

Documentation to read first: `tests/features/advance_phase_refusal.feature` and
`tests/steps/advance_phase_steps.py` (the BDD pattern);
`tests/test_novel_state_mutator_snapshots.py` (the snapshot pattern);
`docs/developers-guide.md` (mutator section) and `docs/users-guide.md` (command
list); AGENTS.md "Snapshot tests" and "end-to-end tests" rules.

Skills to load: `python-router` → `python-testing` (pytest-bdd, syrupy snapshot
discipline); `en-gb-oxendict` for the guide prose; `leta` for navigation.

Edits:

1. `novel_ralph_skill/commands/novel_state.py` `build_app`: register a
   `@app.command def recount() -> CommandOutcome: return mutators.recount()`,
   mirroring the `set_cursor`/`advance_phase` registrations, and update the
   builder docstring to list `recount` as delivered.
2. `tests/features/recount.feature` + `tests/steps/recount_steps.py`: a scenario
   that, given a working tree with two drafted chapters whose hand-typed counts
   are wrong, runs `recount`, then asserts exit `0`, that
   `[word_counts].current` equals the summed token counts and `by_chapter`
   matches per chapter, and that a second `recount` leaves `state.toml`
   byte-for-byte unchanged (the roadmap idempotence + sum success criteria).
   Register the scenario with `scenarios("../features/recount.feature")`
   following the existing step module's structure, and reuse the corpus
   working-tree fixtures. The step that runs `recount` must `chdir` into the
   prepared tree's parent first (the cwd-relative `_state_path()`; Decision Log
   D-CWD), as the advance-phase steps do.
3. `tests/test_novel_state_mutator_snapshots.py` (extend): a `recount` success
   envelope snapshot, with nondeterministic fields normalized (no absolute path;
   `working_dir` is the `"working"` token), paired with a semantic assertion
   on the exit code and `ok` (AGENTS.md "pair them with semantic assertions").
4. `tests/test_console_scripts_e2e.py` (extend if it exercises subcommands):
   confirm `novel-state recount` is reachable through the installed console
   script and returns the expected exit code on a prepared tree (e2e per
   AGENTS.md "externally observable workflows … command-line behaviour").
5. Documentation:
   - `docs/developers-guide.md`: in the mutator section, record that `recount`
     re-derives `[word_counts]` from `draft.md` token counts (the shared helper),
     writes a single file with no `[pending_turn]` bracket, returns a write-shaped
     `{current, by_chapter}` result, and keys `by_chapter` by the manifest
     (Decision Log D-KEY/D-PT). Cite design §4.1.
     **You MUST correct *both* of the two places where the guide mis-classifies
     `recount` as multi-file. Correcting only one leaves the source-of-truth doc
     self-contradictory — exactly the failure Round-1 blocking 1 and Round-2
     blocking A flag.**

     - **Edit (a) — lines 467-468.** They currently read "that belongs to the
       genuinely multi-file mutators (`recount`, `reconcile`)"; `recount` does
       not belong there. Rewrite so the `[pending_turn]` bracket "belongs to the
       genuinely multi-file mutators (`reconcile`, `novel-compile`)" — or
       whichever multi-file writers the guide already recognizes — and explicitly
       note that `recount`, like `set-cursor` and `advance-phase`, writes only
       `state.toml` and so opens no bracket.
     - **Edit (b) — lines 202-206, the "Checker/mutator segregation"
       paragraph.** It currently reads "Mutators (`novel-state init`/`set-cursor`/
       `advance-phase`/`recount`/`reconcile` and `novel-compile`) … write
       atomically via a temporary file plus `Path.replace`, bracketed by a
       `[pending_turn]` intent record so a torn multi-file turn is recoverable."
       This wrongly brackets the single-file mutators. Reword so the
       `[pending_turn]` bracket is attributed only to the *genuinely multi-file*
       writers (`reconcile`, `novel-compile`), and the single-file mutators
       (`init`/`set-cursor`/`advance-phase`/`recount`) are named as writing one
       file via `Path.replace` with **no** bracket. Keep the surrounding
       segregation claim (checkers write nothing; a command must not detect *and*
       repair) intact — only the bracketing attribution changes. Take care not to
       imply `init` is multi-file: per the guide's own lines 463-466, `init`
       writes `state.toml` *plus* `log.md` yet still uses no bracket, so describe
       it as single-`Path.replace`-write-per-file, no `[pending_turn]`.

     For *both* edits cite design §4.1 line 271 (recount re-derives only
     `[word_counts]`) and §3.4 lines 240-241 (a recount is *one write among
     several in a turn*, not the command writing several files) in the edited
     prose so both passages agree and the source-of-truth doc is internally
     consistent. After both edits, grep the guide for "`recount`" and confirm no
     remaining sentence implies it is multi-file or bracketed. This resolves
     Round-1 blocking point 1 and Round-2 blocking point A: the plan's single-file
     reading (D-PT) is substantively correct, and the guide must be brought fully
     into agreement rather than left self-contradictory at either line.
   - `docs/users-guide.md`: extend the `novel-state` section with `recount` —
     what
     it does (re-derives word counts from the drafts), that it writes nothing on
     refusal (exit `3`), and that it is idempotent.

Tests/validation for this item: `make all` (Python gates), **plus**
`make markdownlint` and `make nixie` for the two guide edits (AGENTS.md
markdown rules; no Mermaid is added, but `nixie` is run per the standing rule
for markdown changes).

Acceptance: `tests/features/recount.feature` passes (scenario green), the
`recount` snapshot is committed and semantically asserted, the e2e check
passes, and both guides build clean under `make markdownlint`.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-3-1`.

```console
$ git branch --show-current
roadmap-2-3-1
```

Per work item, after edits:

```console
$ make all
... build check-fmt lint typecheck test all pass ...
```

Expect the Python gates (`build check-fmt lint typecheck test`) to pass. For
Work item 3's markdown:

```console
$ make markdownlint
Summary: 0 error(s)
$ make nixie
... no Mermaid diagrams; exits clean ...
```

Expect markdownlint to report no errors over `**/*.md` and nixie to validate
(no Mermaid added; it exits clean). Use `make fmt` to apply Ruff + mdformat
fixes before `check-fmt`.

To prove a new test is meaningful (red-before-green), run just that test before
implementing the production change:

```console
$ UV_CACHE_DIR=.uv-cache uv run pytest -q tests/test_state_wordcount.py
... fails before Work item 1's edit; passes after ...
```

Expect a failure (the helper does not yet exist) before Work item 1's edit and
a pass after. Mirror this for the `recount` body and the BDD scenario.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes; the new tests
  `tests/test_state_wordcount.py` (unit + property), the `recount`
  unit/property tests, the violations-ownership extension, the
  `recount.feature` scenario, the `recount` envelope snapshot, and the e2e
  reachability check all pass. Each new test fails before its production change
  and passes after.
- Lint/typecheck: `make lint` (Ruff, interrogate 100% docstrings, Pylint) and
  `make typecheck` (`ty check`) pass over `novel_ralph_skill tests`.
- Formatting: `make check-fmt` passes (`make fmt` to fix).
- Markdown (Work item 3): `make markdownlint` and `make nixie` pass.
- Audit: `make audit` (`pip-audit`) passes — no new dependency is added.

Behavioural acceptance (a human can verify):

- On a tree with `working/manuscript/chapter-01/draft.md` (3 words) and
  `chapter-02/draft.md` (5 words) and a hand-wrong `[word_counts]`, running
  `novel-state recount` exits `0` and rewrites `current = 8` and
  `by_chapter = { "01" = 3, "02" = 5 }`. A second `novel-state recount` yields
  a byte-for-byte identical `state.toml`.
- On a tree with no `working/state.toml`, `novel-state recount` exits `3` and
  writes nothing.

## Idempotence and recovery

Every step is re-runnable. `recount` is itself idempotent by construction
(second run over unchanged drafts yields identical bytes — pinned by test). The
atomic `write_document_atomically` leaves either the prior or the new
`state.toml`, never a torn file; a failed write unlinks its temp file. Tests use
`tmp_path`-scoped working trees, so reruns do not accumulate state. No
destructive operation is introduced; `recount` never deletes a `working/` file.

## Artefacts and notes

The load-bearing oracle the production count is pinned against:

```python
# tests/working_corpus/_live_draft.py:86-92
draft_paths = sorted((working_dir / "manuscript").glob("chapter-*/draft.md"))
token_counts = [
    len(path.read_text(encoding="utf-8").split()) for path in draft_paths
]
words_total = sum(token_counts)
```

The deterministic body generator that makes expected totals exact:

```python
# tests/working_corpus/_specs.py:205-214 (draft_body)
if word_count <= 0:
    return ""
return " ".join("word" for _ in range(word_count))
```

## Interfaces and dependencies

Libraries/modules to use and why:

- `tomlkit` — the lossless round-trip writer; `recount` edits the live
  `TOMLDocument` and writes through `write_document_atomically` (ADR-002).
- `pathlib` — directory globbing and file reads (`draft.md`).
- `novel_ralph_skill.state` — `load_document`, `document_to_state`,
  `write_document_atomically`, `validate_state`, `State`, `ChapterEntry`, and
  the new `recount_words`.
- `novel_ralph_skill.contract.runner` — `CommandOutcome`, `StateInputError`.
- `novel_ralph_skill.contract.exit_codes` — `ExitCode`.
- No new external dependency. No cuprum surface (Decision Log D-CUPRUM).

Signatures that must exist at the end:

```python
# novel_ralph_skill/state/wordcount.py
def recount_words(
    working_dir: Path,
    manifest: cabc.Sequence[ChapterEntry],
) -> tuple[int, cabc.Mapping[str, int]]: ...

# novel_ralph_skill/commands/_state_mutators.py
def recount() -> CommandOutcome: ...
```

`build_app` (in `novel_ralph_skill/commands/novel_state.py`) gains a `recount`
subcommand; its existing signature (zero-argument builder) is unchanged.

## Revision note

Round 2 (2026-06-24, planning agent) — resolving the three Round-1 Logisphere
blocking points and folding in the three advisories:

- **Blocking 1 (D-PT versus a source-of-truth doc).** `docs/developers-guide.md`
  line 467-468 mis-lists `recount` among the "genuinely multi-file mutators".
  The plan's single-file reading (D-PT) is substantively correct (design §4.1
  line 271; §3.4 lines 240-241), so Work item 3 step 5 now **mandates
  correcting that guide line** as part of the developers'-guide edit, citing
  §4.1/§3.4. The Constraint, the D-PT decision, and the Surprises observation
  were updated to name the defect and the fix, and to cite §4.1 line 271 + §3.4
  lines 240-241 rather than only the guide.
- **Blocking 2 (vacuous malformed-suffix risk/test).** D-KEY builds every path
  from a manifest integer (`f"chapter-{number:02d}"`); no directory-name suffix
  is parsed. The malformed-`chapter-NN`-suffix risk and its Work item 2 test
  were **removed** and replaced with explicit "no directory-name parsing
  exists, so no such test" notes in the Risks section, Work item 2 step 2, and
  the Work item 2 test list.
- **Blocking 3 (absent-versus-undecodable fault boundary).** The plan now pins
  the boundary precisely: `recount_words` catches **only** `FileNotFoundError`
  per chapter and returns `0`; every other `OSError` (`PermissionError`,
  `IsADirectoryError`) and `UnicodeDecodeError` propagates unchanged, and the
  `recount` body re-raises them via
  `except STATE_INPUT_ERRORS … raise StateInputError … from exc` to exit `3`.
  This is spelled out in Work item 1 step 1, Work item 2 step 2 (with the
  verified `STATE_INPUT_ERRORS` tuple at `novel_state.py:85-91`), and tested on
  both sides of the line (absent → `0`, undecodable → exit `3`) in Work items 1
  and 2.
- **Advisories.** Added Decision Log D-CWD (every new test must
  `monkeypatch.chdir(working.parent)` before `recount`, per
  `test_state_mutators_unit.py:200-208`), Decision Log D-CURRENT (`recount`
  defines `current` as the drafted sum and defers compiled-versus-drafts
  reconciliation to 2.3.2), and a Risk plus Work item 2 test for `recount`
  legitimately refusing a previously-`check`-passing state.

This revision affects no remaining-work estimate: the work-item count and order
are unchanged; the edits sharpen the fault boundary, correct one documentation
line, and remove one vacuous test.

Round 3 (2026-06-24, planning agent) — resolving the single Round-2 Logisphere
blocking point and folding in the two Round-2 advisories:

- **Blocking A (a second, uncorrected `recount`-as-multi-file mis-listing).**
  `docs/developers-guide.md` lines 202-206 (the "Checker/mutator segregation"
  paragraph) also brackets `init`/`set-cursor`/`advance-phase`/`recount` with
  the genuinely multi-file writers under a `[pending_turn]` "torn multi-file
  turn" claim — the same misclassification as lines 467-468. Correcting only
  467-468 would leave the source-of-truth doc self-contradictory. **Work item 3
  step 5 now mandates correcting *both* passages** — relabelled as edit (a) for
  467-468 and edit (b) for 202-206 — attributing the `[pending_turn]` bracket
  only to `reconcile`/`novel-compile` and naming the single-file mutators
  (`init`/`set-cursor`/`advance-phase`/`recount`) as `Path.replace`-per-file
  with no bracket, with a grep-for-`recount` consistency check after the edit
  and a note that `init` writes two files yet still uses no bracket. The
  Constraint, the D-PT decision, and the Surprises observation were updated to
  name *both* lines and to cite §4.1 line 271 + §3.4 lines 240-241 for both
  edits. Verified the exact wording at both passages against the worktree's
  `docs/developers-guide.md` before revising.
- **Advisory (design §3.4:242 loose phrasing).** Added Decision Log D-PT-DESIGN:
  the design's "each mutator opens a `[pending_turn]` …" phrasing at §3.4 line
  242 is not treated as contradicting D-PT (the more specific §4.1 governs),
  and the design is not edited by this task — recorded so a future reader does
  not read §3.4:242 as a contradiction.
- **Advisory (property-oracle scope).** Work item 1's property test now states
  plainly that `live_draft_counts` is a **total-only** oracle (it globs present
  drafts, exposes no per-chapter map), so the property pins the **total** while
  the **per-chapter `by_chapter` table** is pinned by the example-based unit
  test; the test docstring must say so.

This revision affects no remaining-work estimate: the work-item count and order
are unchanged; the edits add one documentation correction (a second guide line)
to Work item 3 step 5, add one Decision-Log acknowledgement, and clarify the
property test's oracle scope. No production-code or test-shape change.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
reviews and audits of step 2.3's tasks. Execute each as a small addendum pass —
no plan or design-review cycle: make the change, run `make all` (plus `make
markdownlint`/`make nixie` for Markdown), `coderabbit review --agent`, commit,
and tick the matching roadmap sub-task on merge.

- [x] 2.3.1.1 — Clear the pre-existing ty `possibly-missing-submodule` warning
  on `commands/_recount.py` (from review:2.3.4, low). `make typecheck` is not
  fully clean: ty warns that `tomlkit.items.InlineTable` — the return annotation
  of `_inline_by_chapter` — relies on a submodule that may not have been
  imported. Add a single explicit `import tomlkit.items` so the typecheck gate is
  restored to clean. The warning is pre-existing (present on origin/main) and was
  out of task 2.3.4's scope. Gate with `make all`.
