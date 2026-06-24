# Implement read-only reconciliation detection in `check` and the disk-authoritative write in `reconcile`

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds. Each
revision must remain self-contained: a newcomer with only the current working
tree and this file must be able to finish the work.

Status: DRAFT (revision 4 — round-4 design review resolved)

> Round-4 resolution summary (full detail in the Revision note and Decision
> Log):
> two blocking points were closed.
>
> - **B1 — RECOUNT leaves `[gates]` stale.** A `[word_counts]`-only recount
> cannot
>   in general yield a `gate-ratio-consistent`-clean tree, because the §5.2
>   validator checks gates against the **table** total
>   `sum(by_chapter.values())`
>   (`validate.py:260`) while the corpus derives honest gates from the **draft**
>   total `sum(chapter.draft_words)` (`_variants.py:36-40`), and the headline
>   variant makes those totals differ by construction. Re-deriving gates from
>   the
>   ratio (the Wafflecat alternative) is **rejected as
>   non-disk-authoritative**: a
>   gate flag means "threshold crossed **and** the pass integrated and logged"
>   (`state-layout.md:104,174-177`), which disk does not record, so `reconcile`
>   must never fabricate it. Resolution adopts review option (b), made airtight:
>   Decision Log **D-GATES** pins both word-count reconciliation variants
>   (over-count and the §5.4 under-count) as **strictly sub-threshold** — the
>   phantom/under-count delta moves the `current/target` ratio across **no**
>   30/50/80% boundary — and Work item 4 adds a **post-repair gate-clean test**
>   proving the reconciled tree passes `gate-ratio-consistent`, plus a stated,
>   tested scope boundary that a threshold-crossing done-claim is **out of scope
>   for word-count reconciliation** and is surfaced as a Tolerance escalation,
>   not
>   silently mis-repaired. The headline scenario is delivered for the
>   sub-threshold
>   class, which is the class a `[word_counts]`-only recount can make coherent.
> - **B2 — recount-only narrows §5.4's named reconstruction.** Collapsing §5.4's
>   "reconstruct from on-disk evidence (which chapters carry `done.flag`, what
>   `compiled.md` contains)" down to a `[word_counts]` recount is a
>   **design-level**
>   narrowing (AGENTS.md "Project documentation", lines 181-183), so Work item
>   6 is
>   re-scoped to **require** a design-doc note in §5.4 (and an ADR if the
>   reviewer
>   deems it substantive) recording that the v1 disk-authoritative
>   reconciliation
>   is the `[word_counts]` recount + `[pending_turn]` recovery, with the broader
>   `done.flag`/`compiled.md` reconstruction deferred — **before** the headline
>   code lands (Decision Log **D-DESIGN-NOTE**). Separately, the genuine §5.4
>   worked case — a real `done.flag` over a **non-empty** draft the table
>   **under-counts** — is now named, given its own corpus variant
>   (`done-flag-real-draft-undercount`), and tested end-to-end (Work item 1
>   spec,
>   Work item 4 behavioural + post-repair gate-clean assertion).

## Purpose / big picture

Today `novel-state check` validates only the eight *pure-state* §5.2 invariants
— it reads `working/state.toml` and decides whether the state contradicts
*itself*. It cannot yet detect when `state.toml` has drifted from what is
actually on disk, and there is no command that repairs such drift. The skill
delegates that recovery to the agent's improvisation
(`skill/novel-ralph/references/state-layout.md` "When state is suspect"), which
is exactly the hand-typed, error-prone routine the design retires. This task
delivers the deterministic version of that routine, split along the
checker/mutator boundary (`docs/novel-ralph-harness-design.md` §3.3, §5.4):

- `novel-state check` becomes **disk-aware**. In addition to the pure-state
  invariants it already reports, it reads the `working/` tree, asserts the
  chapter-manifest-to-disk bijection, detects six classes of disk evidence
  (including the new disk-vs-table word-count divergence that realises the
  roadmap's done-claim case), and — when disk is internally consistent but
  `state.toml` is merely *stale* — reports the discrepancy *and the
  reconciliation it implies* in its payload, exiting `4`. `check` still writes
  nothing (design §3.3).
- `novel-state reconcile` is a new mutator. It recomputes the same
  reconciliation **independently** (it never trusts a payload handed to it),
  writes the reconciled `state.toml`, appends a recovery entry to
  `working/log.md` as the audit receipt, and deletes no file under `working/`.

The reconciliation is **loud, never silent** (design §5.4). Where disk
*contradicts itself* — a `done.flag` beside an empty or absent `draft.md`, a
`compiled.md` referencing a chapter with no `draft.md`, or a non-bijective
manifest — neither `check` nor `reconcile` repairs: both report, log (reconcile
only), and exit `4` so the agent adjudicates.

After this change a user can, from a project's process directory, see the
recovery routine run as code rather than by hand:

```console
$ novel-state check          # state claims a chapter done; the drafts disagree
{"command": "novel-state", "ok": false, "result": {"violations": ["word-counts-match-drafts"],
 "reconciliation": {"action": "recount", "current": 41280, "by_chapter": {"01": 3200, ...}}}, ...}
$ echo $?
4
$ novel-state reconcile      # carry out the reconciliation check reported
{"command": "novel-state", "ok": true, "result": {"action": "recount", "current": 41280, ...}}, ...}
$ echo $?
0
$ novel-state check          # now coherent
{"command": "novel-state", "ok": true, "result": {"violations": []}, ...}
$ echo $?
0
```

You can see it working through the new behavioural scenarios in
`tests/features/reconcile.feature` (a stale tree is detected by `check` at exit
`4`, repaired by `reconcile`, and re-checked clean; a contradictory-evidence
tree is refused by both at exit `4`) and the machine-mode envelope snapshots,
all described under "Validation and acceptance".

## Outcome in one sentence

`novel-state check` reads disk and reports the reconciliation a stale
`state.toml` implies (exit `4`, no write), `novel-state reconcile` carries that
reconciliation out and logs it (exit `0`), and both refuse contradictory disk
evidence loudly (exit `4`) — turning the skill's improvised "when state is
suspect" routine into deterministic code.

## Controlling decision: what `reconcile` actually rewrites (read this first)

The roadmap's lead success case (`docs/roadmap.md:651-652`) is "a scenario
where state claims a chapter is done but no `done.flag` exists is detected by
`check` (exit 4) and repaired by `reconcile`." This is a **steady-state
divergence**: a *settled* `state.toml` (no `[pending_turn]`) whose done-derived
fields disagree with the on-disk manuscript. The design names exactly this case
and the reconstruction direction in design §5.4 lines 489-492: "when [`check`]
finds state merely *behind* disk — for example, state claims a chapter is not
done but a `done.flag` exists — it reconstructs the intended state from on-disk
evidence (which chapters carry `done.flag`, what `compiled.md` contains)." The
roadmap clause is the inverse direction of the very same mechanism, and §5.4
makes disk authoritative either way.

**Where does `state.toml` encode "a chapter is done"?** There is no per-chapter
`done` boolean (`schema.py:73-92` — `ChapterEntry` carries only `number`,
`slug`, `title`, `target_words`). Done-ness is recorded indirectly, and the
design's disk-authoritative basis for it is the **per-chapter word count**:
`word_counts.by_chapter["NN"]` (`schema.py:228-260`). A chapter that is "done"
on disk has a non-empty `working/manuscript/chapter-NN/draft.md` (a positive
token count) and a `working/manuscript/chapter-NN/done.flag`; the matching
state record is a positive `by_chapter["NN"]`. The roadmap's "state claims a
chapter is done but no `done.flag` exists" is therefore the case where
`state.toml`'s `[word_counts]` (and the gates and cursor derived from it)
carries a done chapter that disk does not corroborate — and its inverse, "disk
has a `done.flag` and a real draft the table under-counts," is the §5.4 worked
direction. Both are a single disk-vs-table word-count divergence, repaired by
**re-deriving `[word_counts]` from the drafts** — the same arithmetic `recount`
performs, but fired by a genuine disk-evidence detector and emitted as a
*reconciliation*.

**The §5.4 worked example is the under-count direction, and this plan now tests
it directly (round-4 blocking point B2).** Design §5.4 lines 489-492 names
"state claims a chapter is *not* done but a `done.flag` exists" — a chapter
that *did* finish on disk (`done.flag` present, `draft.md` non-empty) whose
`[word_counts]` table the state under-counts. Crucially this is **not** the
`done-flag-without-draft` contradiction: that oracle predicate fires only on
`has_done_flag and draft_words == 0`
(`tests/working_corpus/_oracle.py:206-215`), so a `done.flag` beside a
**non-empty** draft never trips it. A real `done.flag` over a non-empty draft
the table under-counts therefore lands cleanly as `word-counts-match-drafts` →
`RECOUNT` — the genuine §5.4 "behind disk" case. The round-3 plan only built
the *over-count* headline (a phantom positive table entry over an empty draft,
no flag); it never named or tested the §5.4 under-count case the design
actually wrote down. This revision adds the corpus variant
`done-flag-real-draft-undercount` (Work item 1) and tests it end-to-end (Work
item 4), so the design's worked example is exercised, not merely the inverse
the round-3 variant chose. Both directions are a single disk-vs-table
word-count divergence repaired by the same `RECOUNT`, and both are held
strictly sub-threshold (D-GATES) so the recount yields a
`gate-ratio-consistent`-clean tree.

The detector that fires this case did **not** exist before this task. The
pure-state `by-chapter-sum` invariant (`validate.py:144-154`) compares
`sum(by_chapter) == current` *within* the table and has, by the developers'
guide's own words (`developers-guide.md:366-367`), "no live analogue"; it never
reads disk and so cannot see a table that is internally consistent but stale
against the drafts. This task adds the missing disk-vs-table detector as a new
**disk-evidence** invariant, `word-counts-match-drafts`, that recomputes the
**per-chapter** drafted token counts from disk and reports when the table
disagrees. The production read is the already-shipped `recount_words`
(`novel_ralph_skill/state/wordcount.py:86`), which returns
`(current, by_chapter)` — a per-chapter mapping keyed by the manifest, the
exact shape this predicate compares against `[word_counts]`. The corpus
`live_draft_counts` (`tests/working_corpus/_live_draft.py:69`) is the **wrong**
reference twin: it returns `(drafted_words_total, drafted_chapters_count)` — a
total and a chapter *count*, with **no per-chapter mapping** — so a per-chapter
divergence cannot be pinned equal to it (round-3 blocking point 1). The
deliberate twin is therefore a **new per-chapter disk oracle** in the corpus,
`_check_word_counts_match_drafts` (`tests/working_corpus/_oracle.py`), which
globs `manuscript/chapter-*/draft.md`, splits each present body, derives the
per-chapter mapping straight from disk, and compares it against the table read
from the materialised `state.toml` — the per-chapter analogue of the existing
totals-only `_check_by_chapter_sum_live` (`_live_draft.py:95`). Production
`check_disk_evidence` and the new corpus oracle each read disk independently
and a test pins their per-chapter verdicts equal on every corpus tree (the
deliberate-twin policy, `developers-guide.md:371-379`).

This plan therefore scopes `reconcile`'s **repairs** to two state→disk
corrections that are deterministically recomputable from disk and that the
design authorises:

1. **Stale `[word_counts]` vs the drafts** — the roadmap's headline done-claim
   divergence and the §5.4 worked example. Detected by the new
   `word-counts-match-drafts` disk-evidence invariant; repaired by re-deriving
   `current` and `by_chapter` from the drafts (reuse `recount_words`, the
   already-shipped task-2.3.1 helper) and writing them. This is `RECOUNT`, but
   — unlike the deliberate `recount` *command* — it is fired only by a
   disk-vs-table discrepancy `check` first reports, never unconditionally.

   **This `RECOUNT` rewrites `[word_counts]` only; it does not touch `[gates]`,
   exactly as the task-2.3.1 `recount` command does (`_recount.py:145-149`).**
   The knitting gates are a derived projection: the §5.2
   `gate-ratio-consistent` validator (`validate.py:247-275`) checks each gate
   flag against the `sum(by_chapter.values())/target` ratio. A
   `[word_counts]`-only recount that *changes which 30/50/80% thresholds the
   total crosses* would therefore leave the gates stale and the post-repair
   tree would fail `gate-ratio-consistent`, exiting `4` — the recovery routine
   would loop (round-4 blocking point B1). Re-deriving the gate booleans from
   the recounted ratio is **not** a valid fix: a gate flag records "threshold
   crossed **and** the pass integrated and logged"
   (`skill/novel-ralph/references/state-layout.md:104,174-177`; design §5.2
   line 469-470 frames the gate as *consistent with* the ratio, true only *if*
   crossed — eligibility, not an automatic flip), which is an agent action disk
   does not record; synthesising it would violate "disk is authoritative, never
   the reverse". The scope is therefore pinned by Decision Log **D-GATES**: a
   `word-counts-match-drafts` reconciliation is in scope **only when the
   disk-vs- table delta crosses no gate threshold** (the post-recount ratio
   crosses exactly the thresholds the recorded gates already reflect), so the
   recounted tree is `gate-ratio-consistent`-clean and `check` exits `0`. A
   done-claim divergence large enough to move a gate is a **Tolerance breach**
   (Tolerances "Gate-crossing divergence"): `reconcile` reports it and
   escalates rather than mis-repairing, because integrating a knitting pass is
   the agent's judgemental act, not a deterministic recompute. Both word-count
   variants (the over-count headline and the §5.4 under-count worked case) are
   constructed sub-threshold and pinned by a post-repair gate-clean test (Work
   item 4).
2. **`[pending_turn]` recovery** (complete or roll back per what landed) — the
   design's torn-turn worked example (design §3.4 lines 246-250, §5.4 lines
   502-510) and the roadmap's "uncleared `[pending_turn]`" clause. This covers
   the *transient* mid-turn case; item 1 covers the *settled* steady-state case
   the roadmap headline names.

Every other disk-evidence detection is a **contradiction**, refused loudly by
both commands (exit `4`, reconcile logs it, neither repairs): the manifest-disk
bijection break, the `done.flag`-beside-empty/absent-`draft.md` case, the
`compiled.md`-references-absent-chapter case, and the `cursor-plan-present`
break. A contradiction and a `cursor-plan-present` break are both
**reported-but-not-repaired** (see Decision Log D-REPORT for why
`cursor-plan-present` is reported-not-repaired rather than a contradiction):
`check` exits 4 with the discrepancy and a reconciliation whose action is
`REFUSE` (no repair implied), and `reconcile` exits 4, logs the refusal, and
writes no state change.

This scoping is recorded as Decision Log **D-SCOPE** and pinned by tests (Work
items 1-6). The two scope questions the round-1 plan left open are now closed
against the design and the corpus, not deferred: the steady-state done-claim
divergence is delivered by item 1 (D-SCOPE, D-WORDCOUNT), and
`cursor-plan-present`'s reconcile action is `REFUSE` (D-REPORT). If
implementation nonetheless reveals the design intends `reconcile` to rewrite a
state field this plan has not identified, that remains a **Tolerance breach**
(see Tolerances "Reconciliation scope") — stop and escalate rather than
inventing a new state field.

## Constraints

Hard invariants that must hold throughout. Violation requires escalation, not a
workaround.

- **`check` is strictly read-only.** It must not write `state.toml`, `log.md`,
  `compiled.md`, or any file under `working/`, on any path including the
  disk-evidence and contradiction paths (design §3.3 table; §5.4 line 494). A
  byte-for-byte tree-unchanged test gates this (extends the existing
  `test_check_writes_nothing`).
- **`reconcile` deletes no file under `working/`.** Rolling back a
  `[pending_turn]` clears the record in `state.toml` and leaves the partial
  artefacts on disk, unreferenced. Completing a `[pending_turn]` writes the
  remaining *recomputable* artefact (see Decision Log **D-COMPLETE** for
  exactly what "completing" writes and why it never fabricates prose) and then
  clears the record. Removing a file is never a reconciliation (design §5.4
  lines 497, 505-510). A test asserts the set of files present before reconcile
  is a subset of the set after.
- **`reconcile` recomputes independently.** It must not consume a payload from
  `check`; it derives the reconciliation from disk afresh (design §5.4 line
  496). The two share the *detection/derivation* code, not a serialized handoff.
- **Loud reconciliation.** Every discrepancy `reconcile` resolves is both in the
  envelope `result` and appended to `working/log.md` as a recovery entry; a
  refused contradiction is reported and logged too (design §5.4 lines 499-501,
  516-517). `check` reports but does not log (it writes nothing).
- **Disk is authoritative; `state.toml` describes disk; never the reverse**
  (design §5.4 line 488; state-layout.md line 286).
- **Reconcile repairs only where disk is internally consistent and state is
  merely stale; it refuses — loudly — where disk contradicts itself, and
  likewise reports-but-does-not-repair the `cursor-plan-present` break it
  cannot resolve without fabricating a plan** (design §5.4 lines 517-519;
  Decision Log D-REPORT).
- **The five reserved disk-evidence invariant names must be reused verbatim, and
  the one new name is added in one place.** `manifest-disk-bijection`,
  `done-flag-without-draft`, `compiled-matches-drafts`, `pending-turn-cleared`,
  and `cursor-plan-present` are already defined in the corpus oracle
  (`tests/working_corpus/_oracle.py:48-58`) and named in the developers' guide
  (§"Invariant validation", lines 309-314) as "task 2.3.2's". The production
  `check` must emit these exact strings. This task adds **one** new
  disk-evidence name, `word-counts-match-drafts` (the disk-vs-table per-chapter
  word-count divergence — the detection signal the round-1 plan lacked;
  Decision Log **D-WORDCOUNT**), defined once in the production `disk_evidence`
  module and mirrored into the corpus oracle's `CORPUS_INVARIANT_NAMES` so the
  two vocabularies stay equal (pinned by the existing
  `test_owned_names_equal_corpus_vocabulary` discipline). Do not invent any
  further names; a need for one is a Tolerance breach.
- **Word-count algorithm is fixed and shared.** A chapter's word count is
  `len(draft_text.split())` over the UTF-8 body of
  `working/manuscript/chapter-NN/draft.md`, via the existing
  `novel_ralph_skill.state.wordcount.recount_words`. Do not write a second
  counting rule (design §4.1; roadmap-2-3-1 Constraint "Word-count algorithm").
- **`RECOUNT` rewrites `[word_counts]` only and never `[gates]`; word-count
  reconciliation is in scope only for sub-threshold divergences.** The §5.2
  `gate-ratio-consistent` validator checks each knitting-gate flag against the
  `sum(by_chapter.values())/target` ratio (`validate.py:247-275`). A gate flag
  encodes "threshold crossed **and** the pass integrated and logged"
  (`skill/novel-ralph/references/state-layout.md:104,174-177`) — an agent
  action disk does not record — so `reconcile` must **not** re-derive or
  fabricate gate booleans (that would violate "disk authoritative, never the
  reverse"; round-4 blocking point B1, resolution (a) rejected). Consequently a
  `word-counts-match- drafts` reconciliation is valid **only when the recounted
  total crosses exactly the 30/50/80% thresholds the recorded gates already
  reflect** — i.e. the disk-vs- table delta moves the ratio across no gate
  boundary — so the recounted tree is `gate-ratio-consistent`-clean and the
  follow-up `check` exits `0`. A done-claim divergence large enough to cross a
  gate is a **Tolerance breach** ("Gate-crossing divergence"): `reconcile`
  reports and escalates rather than mis-repairing (Decision Log **D-GATES**). A
  post-repair gate-clean test gates this (Work item 4).
- **The §5.4 recount-only narrowing is a design-level decision and must be
  recorded in the design document before the headline code lands.** Collapsing
  §5.4's "reconstruct the intended state from on-disk evidence (which chapters
  carry `done.flag`, what `compiled.md` contains)" (design §5.4 lines 489-492)
  down to the `[word_counts]` recount + `[pending_turn]` recovery changes what
  the §5.4 reconciliation *reads*, so per AGENTS.md "Project documentation"
  (lines 181-183) it requires a design-doc note in §5.4 (and an ADR if the
  reviewer judges it substantive), not merely this plan's Decision Log (round-4
  blocking point B2; Decision Log **D-DESIGN-NOTE**). Work item 6 writes that
  note as a *gating* deliverable, not a conditional one.
- **Compile divergence uses the §4.3/§9 content model.** Whether `compiled.md`
  matches the drafts is decided by recomputing the ordered concatenation of the
  present drafts and comparing bytes — never a separator/heading grammar the
  design does not define. The corpus oracle's `_check_compiled_matches_drafts`
  (`tests/working_corpus/_oracle.py:228-242`) is the reference model;
  production may share the join helper but must agree byte-for-byte. The full
  compile-and- hash routine is roadmap task 4.1.1's; this task needs only the
  *divergence verdict*, computed the same way (Decision Log D-COMPILE).
- **Lossless `tomlkit` round-trip and atomic writes.** `reconcile` loads through
  `load_document` (`tomlkit`, not `tomllib`), edits the live `TOMLDocument` in
  place, and writes through `write_document_atomically` (temp-file +
  `Path.replace`), preserving comments and layout (ADR-002; design §5.3, §3.4).
  It must not re-serialise from the typed `State` read view.
- **`reconcile` is the project's first genuinely multi-file mutator, and its log
  receipt must land *inside* the bracket.** When it recounts (or completes a
  torn turn) it touches `state.toml` *and* appends the recovery receipt to
  `log.md`. Per the developers' guide (§"Checker/mutator segregation", lines
  205-207) the genuinely multi-file writers (`reconcile`, `novel-compile`)
  bracket their writes with a `[pending_turn]` record so the multi-file turn is
  itself recoverable. The existing `pending_turn` **context manager**
  (`document.py:197-242`) clears the record and writes `state.toml` on clean
  `__exit__` — it knows nothing about `log.md`, so a log append placed *after*
  the `with` block runs after the record is already cleared, leaving a crash
  window with state written, the record gone, and no receipt (round-2 blocking
  point 5). Reconcile must therefore **not** use the context manager for its
  recovery write. It uses the lower-level seam manually, in this exact order
  (Decision Log **D-SELF**, **D-LOG**): (1)
  `open_pending_turn(document, operation="reconcile", paths=["state.toml", "log.md"])`
  then `write_document_atomically` — the intent record lands first; (2) apply
  the state edit to the *same* document (the recounted `[word_counts]`, or the
  `[pending_turn]` clear for the recovered turn); (3) append the recovery line
  to `working/log.md`; (4) `clear_pending_turn(document)` then
  `write_document_atomically` — the reconcile bracket clears **last**, after
  both the state edit and the log receipt are on disk. A crash between any two
  steps leaves a populated `[pending_turn]` with `operation="reconcile"` that a
  subsequent `reconcile` re-derives and finishes; a crash *after* step 4 leaves
  a coherent tree. This honours design §3.4 lines 243-245 ("the record cleared
  *after* every artefact … is written and verified" and "the log entry is
  appended last as the receipt") with no unrecoverable window. Recovering a
  torn turn must not itself corrupt state irrecoverably (D-SELF).
- **Exit-code contract.** A reconciliation finding (stale state, or a refused
  contradiction) exits `4` (`ACTIONABLE_FINDING`). A missing/unparseable
  `state.toml` or absent `working/` exits `3` (`STATE_ERROR`, via
  `StateInputError`). A coherent tree exits `0`. `reconcile` on a coherent tree
  (nothing to repair) exits `0` with an empty action set. Never exit `1` from
  these paths (design §3.2; `contract/exit_codes.py`).
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, comments, and
  commit messages, except verbatim external-API names (AGENTS.md).
- **400-line file cap.** No source or test module exceeds 400 lines (AGENTS.md
  lines 24-27). The disk-evidence detection, the reconcile body, and their
  tests must be split across modules to honour this (see "Plan of work" for the
  layout).

## Tolerances (exception triggers)

Stop and escalate — do not work around — when any of these is reached:

- **Reconciliation scope.** The two scope forks the round-1 plan left open are
  resolved in this revision and are **no longer** open questions: the
  steady-state done-claim divergence is detected by the new
  `word-counts-match-drafts` invariant and repaired by `RECOUNT` (D-SCOPE,
  D-WORDCOUNT), and `cursor-plan-present` is reported-but-not-repaired with
  action `REFUSE` (D-REPORT). This tolerance now triggers only if
  implementation reveals a *further* roadmap success clause that requires
  `reconcile` to rewrite a state field outside the two corrections named in
  Decision Log D-SCOPE (`[word_counts]` recount, `[pending_turn]` recovery) or
  to add a new `state.toml` field — in which case stop and escalate with the
  specific clause and the candidate field. Do not invent state shape.
- **Gate-crossing divergence.** If a real stale tree presents a
  `word-counts-match-drafts` divergence whose recounted total crosses a
  knitting- gate threshold (30/50/80%) the recorded gates do not already
  reflect — so a `[word_counts]`-only recount would leave
  `gate-ratio-consistent` failing — stop and escalate. `reconcile` must report
  the divergence and the gate conflict and exit `4`, **not** silently re-derive
  the gate booleans (that is the agent's judgemental "integrate and log the
  pass" act, not a deterministic recompute; Decision Log D-GATES). This
  Tolerance bounds the headline scenario to the sub-threshold class a
  word-count recount can make coherent; widening it to re-project gates is a
  design-level decision requiring a design-doc/ADR change, not an in-plan
  workaround.
- **Scope (size).** If the production change exceeds **6 files** or **~550 net
  lines** of non-test code, stop and escalate. (The detection and reconcile
  bodies are expected to be three or four small modules.)
- **Dependencies.** If any work item appears to need a new external dependency,
  stop and escalate. This task adds none: it reuses `cyclopts`, `tomlkit`,
  `cuprum` (tests only), `pytest`, `pytest-bdd`, `syrupy`, and `hypothesis`,
  all already locked.
- **Public-interface change.** If `build_app()`'s zero-argument signature, the
  `CommandOutcome`/`RunContext` contract, the `Envelope` field set, or the
  `validate_state` signature must change, stop and escalate. This task *adds* a
  subcommand and *adds* a disk-evidence detection function; it changes no
  existing signature.
- **Iterations.** If a gate (`make all`) still fails after **5** fix attempts on
  one work item, stop and escalate with the failing output.
- **Time.** If any single work item exceeds **4 hours**, stop and escalate.
- **Ambiguity.** If a roadmap clause admits two materially different
  implementations after consulting the design, present both with trade-offs and
  escalate rather than choosing silently.

## Risks

- Risk: The "state claims a chapter done" scenario has no state field to repair,
  so the reconciliation is mis-modelled (round-2 blocking point 1). Severity:
  high | Likelihood: low (resolved by design) Mitigation: Decision Log
  D-SCOPE/D-WORDCOUNT pin the interpretation: done-ness is recorded in
  `word_counts.by_chapter` (`schema.py:228-260`), the done-claim divergence is
  the disk-vs-table word-count mismatch detected by the new
  `word-counts-match-drafts` invariant, and the repair is `RECOUNT`. This is
  the §5.4 lines 489-492 worked direction ("reconstructs the intended state
  from on-disk evidence"), not a new field. Work item 1 builds the detector
  (twinned against a **new per-chapter disk oracle**
  `_check_word_counts_match_drafts`, not the totals-only `live_draft_counts` —
  round-3 blocking point 1); Work item 4 builds a
  `done-claim-stale-word-counts` corpus variant (a settled tree, no
  `[pending_turn]`, `has_done_flag=False`, a positive `by_chapter_override`
  table entry over an empty/absent draft so **only** `word-counts-match-drafts`
  fires — round-3 blocking point 2) and proves `check` exits 4 and `reconcile`
  repairs it. If the headline scenario cannot be delivered within D-SCOPE, it
  is a Tolerance breach.
- Risk: The disk-vs-table word-count detector double-fires with the pure-state
  `by-chapter-sum` invariant (`validate.py:144-154`), so a single stale table
  reports two violations and the precedence is ambiguous. Severity: medium |
  Likelihood: medium Mitigation: `by-chapter-sum` is table-internal
  (`sum(by_chapter) == current`) and `word-counts-match-drafts` is
  disk-vs-table; they are orthogonal predicates over different inputs. Decision
  Log **D-WORDCOUNT** fixes the precedence: a contradiction dominates, then
  `pending-turn-cleared`, then `word-counts-match-drafts` → `RECOUNT`. A
  recount makes both pass by construction (`current = sum(by_chapter)`), so
  `reconcile` is idempotent. The Work item 2 property test asserts the
  precedence is total and deterministic.
- Risk: A `[word_counts]`-only `RECOUNT` leaves `[gates]` stale, so the
  post-repair `check` fires `gate-ratio-consistent` and exits `4` — the
  recovery routine loops (round-4 blocking point B1). Severity: high |
  Likelihood: medium (without the sub-threshold guard) Mitigation: Decision Log
  **D-GATES** and the Constraint pin word-count reconciliation to
  **sub-threshold** divergences (the recounted ratio crosses exactly the
  thresholds the recorded gates reflect), so the recount leaves
  `gate-ratio-consistent` satisfied. The two word-count variants are built
  sub-threshold and a **post-repair gate-clean test** (Work item 4) asserts the
  reconciled tree passes `gate-ratio-consistent`; an idempotent follow-up
  `check` exits `0`. A real threshold-crossing divergence is a Tolerance breach
  ("Gate-crossing divergence") — `reconcile` reports and escalates, never
  fabricates the "integrated and logged" gate flag disk does not record. The
  `recount` command's own `_refuse_if_incoherent` (`_recount.py:148`) is the
  belt-and-braces backstop: a gate-inconsistent proposed recount would refuse
  rather than write a broken tree.
- Risk: The §5.4 recount-only narrowing is recorded only in this plan's Decision
  Log, leaving the design document silent on a design-level scope change
  (round-4 blocking point B2). Severity: medium | Likelihood: low (closed by
  D-DESIGN-NOTE) Mitigation: Work item 6 writes a §5.4 design-doc note (and an
  ADR if the reviewer judges it substantive) recording that the v1
  disk-authoritative reconciliation is `[word_counts]` recount +
  `[pending_turn]` recovery, with the broader `done.flag`/`compiled.md`
  reconstruction deferred, **before** the headline code merges. The genuine
  §5.4 under-count worked case is added as the
  `done-flag-real-draft-undercount` variant and tested (Work items 1, 4).
- Risk: `check` and `reconcile` drift — `check` reports a reconciliation
  `reconcile` then computes differently. Severity: high | Likelihood: medium
  Mitigation: Both call **one shared pure derivation function**
  (`derive_reconciliation(state, working_dir) -> Reconciliation`); `check`
  renders it read-only, `reconcile` enacts it. A cross-check test asserts the
  action `check` reports equals the action `reconcile` enacts on the same tree
  (Work item 6).
- Risk: A disk-evidence detector disagrees with the corpus oracle, so the
  corpus's named variants no longer pin the production behaviour. Severity:
  medium | Likelihood: medium Mitigation: The corpus oracle
  (`tests/working_corpus/_oracle.py`) is the independent twin; an agreement
  test (Work item 3, mirroring
  `test_validate_state_corpus.py::test_incoherent_agreement_restricted_to_owned`)
  pins the production disk-evidence detector to the oracle's verdict on every
  corpus tree and variant.
- Risk: `reconcile`'s own multi-file write is itself torn and corrupts state.
  Severity: medium | Likelihood: low Mitigation: Reconcile brackets its writes
  with the **manual** `open_pending_turn` / state-edit / `log.md`-append /
  `clear_pending_turn` sequence — **not** the `pending_turn` context manager
  (Decision Log **D-SELF**; the context manager clears on `__exit__` with no
  pre-clear log hook, round-2 blocking point 5 / round-4 advisory A3). A crash
  at any step leaves a populated `operation="reconcile"` record a subsequent
  `reconcile` re-derives and finishes; a self-recovery test (Work item 6)
  covers it.
- Risk: A leaked `tomlkit` temp file or a non-idempotent reconcile write.
  Severity: low | Likelihood: low Mitigation: Reuse `write_document_atomically`
  (unlinks the temp file on failure) and the recount idempotence pattern
  (rebuild `by_chapter` as a fresh ordered inline table); an idempotence test
  asserts a second reconcile over an already-reconciled tree is a byte-for-byte
  no-op write (or a clean exit-0 no-op).
- Risk: `log.md` append is not atomic / corrupts the log on a crash.
  Severity: low | Likelihood: low Mitigation: The recovery entry is appended as
  the *receipt*, last, after the state write succeeds (design §3.4 line 237
  "the log entry is appended last as the receipt"); a torn append loses only
  the receipt, not state. Decision Log D-LOG records the append-last ordering
  and the entry format.

## Progress

- [x] Work item 0 — Orientation and red baseline (no production code).
  Scaffold `tests/test_reconcile_scaffold.py` lands the runtime import spine.
  **Deviation (D-SCAFFOLD-XFAIL):** the plan asks for a test that "fails at
  import (red baseline)", but committing a hard-failing test would breach the
  per-work-item `make all` gate (and a literal `from … import` of the missing
  module is an *error-level* `ty` diagnostic, not a runtime fault). Resolved by
  (a) importing through `importlib.import_module` so the static type-checker
  does not resolve-and-fail the not-yet-existent module at gate time, and (b)
  marking the test `xfail(strict=True, raises=ModuleNotFoundError)` so it is an
  *expected* failure (green gate) that still proves the import spine. Work item
  4 removes the marker, flipping it green; a strict xfail that unexpectedly
  passes is itself a failure, so the marker cannot silently outlive the module.
  CodeRabbit (1 run, 1 minor): added a message to the bare `assert`.
- [x] Work item 1 — Disk-evidence detection module (pure functions over a
  `working/` path), the five reserved names plus the new
  `word-counts-match-drafts`. Lands `novel_ralph_skill/state/disk_evidence.py`
  (`check_disk_evidence`, the six name constants,
  `DISK_EVIDENCE_INVARIANT_NAMES`, and the exported `disk_word_counts`
  reconcile-payload helper) plus the shared
  `novel_ralph_skill/state/compile_model.py` join helper, both re-exported from
  `state/__init__.py`. The corpus gains the disk-reading oracle
  `_check_word_counts_match_drafts` (wired into `corpus_check`), the
  `WORD_COUNTS_MATCH_DRAFTS` name, and the `done-flag-real-draft-undercount`
  §5.4-worked variant. Tests: `tests/test_disk_evidence.py`. **Decision
  (D-WC-BY-CHAPTER-ONLY):** the `word-counts-match-drafts` predicate compares
  the **per-chapter `by_chapter` mapping only**, never `current`. The plan's
  "or its derived `current`" phrasing would make it overlap the table-internal
  `by-chapter-sum` invariant (any `current != sum(by_chapter)` also disagrees
  with the disk recount), breaking the single-invariant isolation of the
  `by-chapter-sum-mismatch` variant. Comparing `by_chapter` only keeps the two
  orthogonal exactly as D-WORDCOUNT requires; a `RECOUNT` rewrites both, so
  both pass post-repair. **Decision (D-WC-SHARED-KEYS):** the predicate
  compares only the **shared** chapter keys, so a manifest-to-disk key-set
  mismatch (the `manifest-extra-entry` contradiction) does not double-fire
  here. Both decisions are mirrored in the corpus oracle twin. **Knock-on:** the
  `DIVERGENT_TABLE_VARIANTS` over-count tree genuinely *is* a disk-vs-table
  divergence, so `corpus_check` now names a third invariant on it;
  `test_divergent_table_breaks_both_proxies` and the
  `_DEFERRED_INVARIANT_NAMES` / `_DISK_EVIDENCE_NAMES` frozensets in the
  validator suites were updated to add `word-counts-match-drafts`. CodeRabbit
  (1 run, 1 trivial): added assertion messages.
- [x] Work item 2 — The shared `derive_reconciliation` pure function (total
  precedence: refuse / pending-turn / recount / none). Lands
  `novel_ralph_skill/state/reconcile.py` (`ReconcileAction`, `Reconciliation`,
  `derive_reconciliation`), re-exported from `state/__init__.py`. The
  pending-turn classifier takes the already-narrowed `PendingTurn` (avoids a
  bare production `assert` the lint rules forbid), strips the `working/` prefix
  via `removeprefix`, and extracts basenames via `PurePosixPath(...).name`
  (CodeRabbit: pathlib over string manipulation). Tests:
  `tests/test_reconcile_derivation.py` — a table-driven action map over every
  materialising corpus variant, an inline unrecoverable-torn-turn ROLLBACK
  case, a RECOUNT payload assertion, and a Hypothesis property pinning totality
  - "no disk-evidence violation yields NONE" over generated torn-turn
  declared-path sets (`python-verification`: example tests cannot exhaust the
  declared-path space). CodeRabbit (1 run, 1 critical + 1 major): fixed the
  test import to the public façade and the basename extraction to pathlib.
- [x] Work item 3 — Wire disk-evidence detection into `check`; agreement test
  against the corpus oracle. `novel_state.py::_check()` now unions
  `validate_state` and `check_disk_evidence` into `result.violations`, attaches
  the `derive_reconciliation` payload to `result.reconciliation` when disk
  evidence fired, and exits `4`; a disk-read fault routes to exit `3` via
  `_disk_evidence_or_state_error` (the same `STATE_INPUT_ERRORS` wrap `recount`
  uses). `check` writes nothing on any path. Tests:
  `tests/test_novel_state_check_disk.py` — behavioural exit-4 + reconciliation
  per disk-evidence class, coherent-tree-no-reconciliation, the strengthened
  writes-nothing guard, the whole-corpus union-vs-oracle agreement test, and
  two redaction-free machine-envelope snapshots (recount + refuse), each paired
  with a semantic action assertion. CodeRabbit (1 run): 2 majors, both in
  pre-existing planning review-note docs (`*.review-round-3.md`/`-4.md`)
  outside this work item's deliverables — skipped as out of scope (not created
  or edited by this task).
- [x] Work item 4 — `reconcile` mutator: disk-vs-table recount (over-count
  headline **and** the §5.4 under-count worked case, both sub-threshold) +
  pending-turn recovery via the manual receipt-last bracket, loud logging, no
  deletion, post-repair gate-clean assertion (D-GATES). Lands
  `novel_ralph_skill/commands/_reconcile.py` (`reconcile()`, the D-SELF manual
  bracket `_run_reconcile_bracket`, `_append_recovery_entry`, the per-action
  edit closures, and the write/refuse outcome builders), registered in
  `build_app()`. The scaffold test is flipped from xfail to a plain green smoke
  test. New corpus variants live in
  `tests/working_corpus/_reconcile_variants.py` with the shared
  baseline/helpers extracted to `_variant_base.py` (both keep `_variants.py`
  under the 400-line cap). Tests: `tests/test_reconcile.py` (headline + §5.4
  worked case detected/repaired/gate-clean, disk-derived counts, the
  threshold-crossing scope boundary refusing with exit 3, rollback/complete
  recoveries with no deletion, the sole-violation guard), plus
  `tests/features/reconcile.feature` + `tests/steps/reconcile_steps.py` +
  `tests/test_reconcile_bdd.py`. **Decision (D-COMPLETE-CLEARS):** the bracket's
  `open_pending_turn` step replaces any torn `[pending_turn]` with reconcile's
  own record and step 4 clears it, so the COMPLETE/ROLLBACK edit need not
  itself delete the torn record — both recoveries leave no `[pending_turn]` and
  delete no `working/` file. The threshold-crossing negative fixture confirms
  the D-GATES scope boundary: such a recount refuses with exit 3 via the
  recount-style `_refuse_if_incoherent` backstop rather than writing a
  gate-inconsistent tree. CodeRabbit (1 run, 1 minor): added descriptive
  assertion messages.
- [x] Work item 5 — Refuse-class handling in both `check` and `reconcile`
  (three contradictions plus `cursor-plan-present`), exit `4`, no repair. The
  REFUSE path was already implemented in Work item 4's dispatch; this work item
  finalises it with the comprehensive `tests/test_reconcile_refuse.py` suite:
  all seven refuse-class variants (both done-flag directions, the compile
  divergence, both manifest directions, both cursor-plan variants) exit `4`
  with action `refuse` in **both** commands; `reconcile` leaves `state.toml`
  byte-for-byte unchanged and appends a `refuse` receipt to `log.md`; the
  round-2 blocking-point-4 guard pins `cursor-plan-present` to `refuse`/exit-4
  (never `none`/exit-0); plus a refuse-envelope snapshot paired with a semantic
  action assertion. CodeRabbit (1 run, 0 findings).
- [x] Work item 6 — `check`/`reconcile` cross-check, idempotence, self-recovery,
  and reconcile e2e; documentation updates including the **gating** §5.4
  design-doc note (D-DESIGN-NOTE). `tests/test_reconcile_integration.py` pins the
  cross-check (check's reported action equals reconcile's enacted action on every
  materialising variant; D-SHARED), idempotence (a second reconcile is a `none`
  byte-identical no-op), and self-recovery (an interruption after the receipt but
  before the clear leaves a recoverable `operation="reconcile"` record, and
  repeated reconcile converges the tree). `tests/test_reconcile_e2e.py` adds a fast
  entry-point reachability check and the slow POSIX wheel-build install e2e
  (reusing `_build_and_install_novel_state` verbatim, D-CUPRUM). Docs:
  developers-guide reclassifies the disk-evidence set as **six** invariants and
  records the §3.4-line-237 receipt-ordering deviation; users-guide documents
  disk-aware `check` and the `reconcile` subcommand; the design doc §5.4 carries
  the **gating** D-DESIGN-NOTE (v1 recount-only scope, deferred reconstruction,
  the A2 `cursor-plan-present` → refuse interpretation); roadmap 2.3.2 ticked.
  `test_owned_names_equal_corpus_vocabulary` extended to pin the six-name
  disk-evidence vocabulary. CodeRabbit (1 run, 1 trivial): added assertion
  messages.
  **Decision (D-SELF-CONVERGES):** an interrupted `RECOUNT` converges in two
  recovery passes — the first clears the leftover `operation="reconcile"` record
  (a COMPLETE since `state.toml`/`log.md` exist), the second re-applies the
  still-pending recount. This is consistent with the harness re-entry model
  (idempotent reconcile until `check` is clean); the self-recovery test asserts
  convergence, not single-pass repair.
  **Surprise (D-CHURN):** the worktree arrived carrying ~80 unrelated uncommitted
  doc modifications (the recurring "spurious make-fmt mdformat churn" the repo's
  stash history documents) that broke `make markdownlint` on files whose committed
  versions are clean. Set aside via `git stash` (Safety Net blocked a raw
  `git checkout --`), leaving only this task's five intentional doc edits;
  `make markdownlint` and `make nixie` then pass clean over the touched docs.

## Surprises & discoveries

- Observation: The local cuprum dev checkout at `/data/leynos/Projects/cuprum`
  has drifted from the locked PyPI `cuprum==0.1.0`. Evidence: The checkout's
  `SafeCmd.run_sync` takes `output: RunOutputOptions`, whereas the cached
  locked-0.1.0 wheel
  (`~/.cache/uv/archive-v0/vvzZ1jTMbiIrGZD_2Lryn/cuprum/sh.py:450-455`) takes
  `*, capture=True, echo=False, context=None`, which is the signature the
  existing passing e2e test uses (`tests/test_novel_state_check.py:365-367`).
  Impact: Pin all cuprum usage to the **locked 0.1.0** signature and the
  existing `test_novel_state_check.py` e2e helper, NOT the dev checkout.
  Recorded so a later reader does not "fix" the e2e to the drifted API.

## Decision log

- Decision (**D-SCOPE**): `reconcile` repairs exactly two state→disk drifts —
  stale `[word_counts]` vs the drafts (`RECOUNT`) and `[pending_turn]` recovery
  (complete/rollback) — and refuses everything else (contradictions and
  `cursor-plan-present`) loudly. The roadmap's "state claims a chapter is done
  but no `done.flag` exists" headline is realised as the **steady-state** stale-
  `[word_counts]` case, *not* a pending-turn rollback: a settled tree (no
  `[pending_turn]`) whose `word_counts.by_chapter` records a done chapter the
  drafts do not corroborate, detected by the new `word-counts-match-drafts`
  invariant and repaired by re-deriving `[word_counts]` from disk. The repair
  rewrites `[word_counts]` **only** and never `[gates]`; it is scoped to
  sub-threshold divergences so the recounted tree stays `gate-ratio-consistent`
  (Decision Log **D-GATES**; round-4 blocking point B1). The genuine §5.4
  worked direction — a real `done.flag` over a non-empty draft the table
  under-counts — is the same disk-vs-table divergence and is added as the
  `done-flag-real-draft-undercount` variant (round-4 blocking point B2).
  Rationale: The design defines no per-chapter `done` boolean
  (`schema.py:73-92`); done-ness is recorded in `word_counts.by_chapter`
  (`schema.py:228-260`), and design §5.4 lines 489-492 make disk authoritative
  and name the reconstruction "from on-disk evidence (which chapters carry
  `done.flag`, what `compiled.md` contains)". A recount is the
  disk-authoritative arithmetic that brings the table back to the drafts; it
  (a) repairs deterministically from disk, (b) adds no state field, and (c) is
  exactly §5.4's "state merely behind disk". The round-1 recasting of the
  headline as a *pending-turn rollback* was wrong: a `[pending_turn]` exists
  only mid-torn-turn, whereas the roadmap names a settled divergence (round-2
  blocking point 1). Alternatives (a `[chapters].done` field, or `reconcile`
  touching `done.flag`) either change the schema (Tolerance breach) or make
  `reconcile` *fabricate* manuscript artefacts from a state claim — the reverse
  of "disk is authoritative". Date/Author: 2026-06-24, planning agent (revised
  round 2).
- Decision (**D-WORDCOUNT**): This task adds one disk-evidence invariant,
  `word-counts-match-drafts`, the disk-vs-table per-chapter word-count check.
  The predicate recomputes each chapter's drafted token count from
  `working/manuscript/chapter-NN/draft.md` via the shared `recount_words` helper
  (`novel_ralph_skill/state/wordcount.py:86`; the same `len(text.split())`
  rule, no second counter), keyed by the manifest the predicate derives from
  `state.chapters`, and reports a violation when the recomputed `by_chapter`
  (or the derived `current`) differs from the table. This is the detection
  signal the round-1 plan lacked (round-2 blocking point 2): the pure-state
  `by-chapter-sum` is table-internal with "no live analogue"
  (`developers-guide.md:366-367`) and cannot see a
  stale-but-internally-consistent table. The new predicate's reference twin is
  **not** the corpus `live_draft_counts`
  (`tests/working_corpus/_live_draft.py:69`), which returns only a
  `(drafted_words_total, drafted_chapters_count)` pair and so carries **no
  per-chapter mapping** to pin a per-chapter divergence against (round-3
  blocking point 1). The twin is a **new per-chapter disk oracle**,
  `_check_word_counts_match_drafts` in `tests/working_corpus/_oracle.py`, that
  globs `manuscript/chapter-*/draft.md`, splits each present body into the
  per-chapter mapping straight from disk, and compares it against the table
  read from the materialised `state.toml` — the per-chapter analogue of the
  existing totals-only `_check_by_chapter_sum_live` (`_live_draft.py:95`). It
  reads disk (not the `spec`), because no `WorkingTreeSpec` channel encodes a
  per-chapter table-vs-draft divergence (advisory: round-2 review point 3; the
  spec's `by_chapter_override` sets the table, `draft_words` sets the disk, and
  only the materialised tree carries both). Production carries its own copy
  (deliberate-twin policy) and a test pins the two **per-chapter** verdicts
  equal on every corpus tree. Precedence in `derive_reconciliation`: a
  contradiction dominates, then `pending-turn-cleared`, then
  `word-counts-match-drafts` → `RECOUNT`, else `NONE`. `by-chapter-sum` and
  `word-counts-match-drafts` are orthogonal (table- internal vs disk-vs-table)
  and a recount satisfies both by construction. Rationale: §5.4 makes disk
  authoritative; a disk-authoritative reconciliation needs a disk-reading
  detector, which §5.2's table-internal invariant is not. The recount
  arithmetic is already shipped and shared; reusing it adds no counting rule.
  The corpus already owns the independent disk-reading oracle to pin it to.
  Date/Author: 2026-06-24, planning agent (added round 2).
- Decision (**D-GATES**): A `word-counts-match-drafts` reconciliation
  (`RECOUNT`) rewrites `[word_counts]` **only**; it never writes `[gates]`. It
  is in scope **only when the disk-vs-table delta crosses no knitting-gate
  threshold** — the recounted `sum(by_chapter)/target` ratio crosses exactly
  the 30/50/80% thresholds the recorded gates already reflect — so the
  recounted tree is `gate-ratio-consistent`-clean and the follow-up `check`
  exits `0`. A done-claim divergence large enough to move a gate is a
  **Tolerance breach** ("Gate-crossing divergence"): `reconcile` reports the
  gate conflict and escalates rather than mis-repairing. Rationale: The §5.2
  `gate-ratio-consistent` validator (`validate.py:247-275`, line 260) checks
  gates against the **table** total `sum(by_chapter.values())`, while the
  corpus derives honest gates from the **draft** total
  `sum(chapter.draft_words)` (`_variants.py:36-40`); a stale done-claim makes
  those totals differ by construction (round-4 blocking point B1). Re-deriving
  the gate booleans from the recounted ratio (Wafflecat alternative (a)) is
  **rejected**: a gate flag means "threshold crossed **and** the pass
  integrated and logged" (`state-layout.md:104,174-177`; design §5.2 line
  469-470 frames it as *consistent with* the ratio, true only *if* crossed —
  eligibility, not an automatic flip), an agent judgement disk does not record.
  Synthesising it would violate "disk is authoritative, never the reverse" and
  turn the recovery routine into the "loud but wrong" failure §5.4 warns
  against (Doggylump pre-mortem). Adopting review option (b): the headline is
  delivered for the sub-threshold class — precisely the class a
  `[word_counts]`-only recount can render coherent — pinned by the post-repair
  gate-clean test (Work item 4). The `recount` command's `_refuse_if_incoherent`
  (`_recount.py:148`) backstops any threshold-crossing recount by refusing
  rather than writing an inconsistent tree. Date/Author: 2026-06-26, planning
  agent (added round 4).
- Decision (**D-DESIGN-NOTE**): Narrowing §5.4's named done-claim reconstruction
  ("reconstruct the intended state from on-disk evidence — which chapters carry
  `done.flag`, what `compiled.md` contains", lines 489-492) down to the
  `[word_counts]` recount + `[pending_turn]` recovery this task delivers is a
  **design-level** decision (it changes what the §5.4 reconciliation *reads*).
  Per AGENTS.md "Project documentation" (lines 181-183) it must be recorded in
  the design document — a note in `docs/novel-ralph-harness-design.md` §5.4,
  and an ADR if the reviewer judges it substantive — **not** only in this
  ExecPlan's Decision Log (round-4 blocking point B2). Work item 6 writes that
  note as a **gating** deliverable that lands with (or before) the headline
  code, stating: v1's disk-authoritative `reconcile` repairs (i) stale
  `[word_counts]` vs the drafts (sub-threshold; D-GATES) and (ii) an uncleared
  `[pending_turn]`, and **defers** the broader `done.flag`/`compiled.md`-driven
  reconstruction (e.g. re-deriving a per-chapter done projection or
  re-projecting gates) to a later task. The plan no longer claims the
  recount-only reading is merely an implementation detail. Rationale: The
  reviewer is required to hold the design boundary: the plan must not silently
  relax §5.4 to fit the chosen mechanism. Recording the narrowing in the design
  document makes the boundary explicit and reviewable, and gives the genuine
  §5.4 under-count worked case (`done-flag-real-draft-undercount`, now a tested
  variant) a documented home. Date/Author: 2026-06-26, planning agent (added
  round 4).
- Decision (**D-COMPLETE**): `COMPLETE_PENDING_TURN` is reserved for a torn turn
  whose only *not-yet-landed* declared artefact is one `reconcile` can
  recompute from the drafts — concretely, the `state.toml` `[word_counts]`
  write (a recount) and/or the `working/log.md` receipt. `reconcile`
  "completes" by performing that recompute-and-write and then clearing the
  record, exactly as design §5.4 line 505 ("completing writes the remaining
  artefacts so the turn lands") and the Constraint require. It never fabricates
  a `draft.md` or a `done.flag`: a torn turn whose *unrecoverable* artefact (a
  draft body, a `done.flag`) did not land cannot be completed and is **rolled
  back** instead (the record is cleared, the partial artefacts left on disk,
  design §5.4 lines 506-510). The round-1 plan's contradiction — `COMPLETE`
  only when "all declared paths landed," so it never wrote anything (round-2
  blocking point 3) — is resolved by this split: `COMPLETE` is selected when
  every *missing* declared path is recomputable (`state.toml`/`log.md`), and
  `reconcile` then writes those recomputable paths; otherwise `ROLLBACK`. The
  classifier returns the missing-path set in the reconciliation payload so the
  dispatch knows which recomputable artefact to write. Rationale: This makes
  "completing writes the remaining artefacts" literally true while never
  violating "disk is authoritative" (prose is never invented — only state/log,
  which are derived from disk). It removes the internal contradiction the
  round-1 plan carried. Date/Author: 2026-06-24, planning agent (added round 2).
- Decision (**D-REPORT**): `cursor-plan-present` (a non-zero scene/beat cursor
  with no on-disk `scenes.md`/`beats.md`; oracle `_oracle.py:245-267`, corpus
  variants `scene-cursor-without-plan` / `beat-cursor-without-plan`,
  `_variants.py:158-169`) is a real disk-evidence violation that `check` must
  exit 4 on, but it is **reported-not-repaired**: `reconcile` cannot synthesise
  a missing plan from disk without fabricating planning prose (the reverse of
  "disk authoritative"), and it is not a contradiction between two disk
  artefacts. It maps to `derive_reconciliation` action `REFUSE` — the same
  fourth action a contradiction maps to — so `check` attaches a coherent exit-4
  payload (a `REFUSE` reconciliation naming `cursor-plan-present`) and
  `reconcile` exits 4, logs the refusal, and writes no state change. This
  closes the round-1 control-flow fork where `cursor-plan-present` fell through
  to `NONE` while `check` exited 4 and `reconcile` exited 0 (round-2 blocking
  point 4): with `REFUSE`, the cross-check holds (both report `REFUSE`/exit 4)
  and the `NONE`-means-exit-0 idempotence test is consistent because
  `cursor-plan-present` is never `NONE`. Rationale: An exit-4 finding must
  carry an actionable-but-not-auto-repairable verdict, not "nothing to do".
  Folding `cursor-plan-present` and contradictions into a single `REFUSE`
  action keeps the exit-4 payload, the cross-check, and the idempotence test
  mutually consistent. The action is named `REFUSE` (covering both
  contradictions and reported-not-repaired cursor-plan breaks) rather than
  `REFUSE_CONTRADICTION` so the name does not misdescribe the cursor-plan case;
  the log entry's discrepancy text distinguishes them. Round-4 advisory A2:
  `cursor-plan-present` is the §5.2 invariant-6 sub-clause ("scene/beat zero
  until plans exist", design §5.2 lines 466-468), not a §5.4 disk
  *contradiction*. Giving it §5.4 `REFUSE` semantics (report, log, exit 4, no
  repair) is a defensible design *interpretation*, so Work item 6's §5.4
  design-doc note (D-DESIGN-NOTE) also records this one-line interpretation
  alongside the recount-only narrowing, rather than leaving it only in this
  Decision Log. Date/Author: 2026-06-24, planning agent (added round 2; A2 note
  added round 4).
- Decision (**D-SHARED**): `check` and `reconcile` share one pure derivation
  function `derive_reconciliation(state, working_dir) -> Reconciliation`;
  `reconcile` recomputes it independently (does not consume `check`'s payload),
  honouring design §5.4 line 496 while still guaranteeing they cannot disagree.
  Rationale: Independent recomputation is the design contract; a shared *pure
  function* satisfies it without a serialized handoff, and a cross-check test
  pins the equality. Date/Author: 2026-06-24, planning agent.
- Decision (**D-NAMES**): The production disk-evidence detector emits the five
  already-reserved names verbatim (`manifest-disk-bijection`,
  `done-flag-without-draft`, `compiled-matches-drafts`, `pending-turn-cleared`,
  `cursor-plan-present`), defined in the production state package and pinned
  equal to the corpus oracle's `CORPUS_INVARIANT_NAMES` by a test, mirroring
  the pure-state validator's `PURE_STATE_INVARIANT_NAMES` discipline
  (`validate.py:60-69`). Rationale: One vocabulary across validator, corpus
  oracle, and the §5.4 detector; no drift (developers' guide §"Invariant
  validation"). Date/Author: 2026-06-24, planning agent.
- Decision (**D-COMPILE**): The `compiled-matches-drafts` detection recomputes
  the ordered concatenation of present drafts and compares bytes, sharing a
  join helper with the §4.3 model; the full compile-and-hash command is task
  4.1.1's, out of scope here. The detection treats a missing `compiled.md` as
  satisfied (nothing to diverge from), exactly as the oracle does
  (`_oracle.py:236-237`). Rationale: The divergence *verdict* is all §5.4
  needs; reproducing the oracle's model keeps the corpus pinning honest.
  Date/Author: 2026-06-24, planning agent.
- Decision (**D-SELF**): `reconcile` does **not** use the `pending_turn` context
  manager for its repair write, because that manager clears+writes on
  `__exit__` and offers no hook to append the `log.md` receipt *before* the
  clear (round-2 blocking point 5). Instead it drives the lower-level seam
  manually in the order fixed in the Constraint "first genuinely multi-file
  mutator": (1)
  `open_pending_turn(document, operation="reconcile", paths=["state.toml", "log.md"])`
  - `write_document_atomically` (intent first); (2) the state edit (recount or
  pending-turn clear) on the same document; (3) append the receipt to `log.md`;
  (4) `clear_pending_turn(document)` + `write_document_atomically` (bracket
  cleared last). An exception at any step leaves a populated
  `operation="reconcile"` record on disk that a subsequent `reconcile`
  re-derives and finishes, so an interrupted reconcile is itself recoverable; a
  completed run leaves a coherent tree. A small helper
  `run_reconcile_bracket(path, *, edit, log_line)` may encapsulate steps 1-4 to
  keep `_reconcile.py` under the 400-line cap, but it must follow this exact
  order and must not be the context manager. Rationale: Reconcile is the first
  genuinely multi-file mutator; the developers' guide (lines 205-207) requires
  the bracket, design §3.4 lines 243-245 require the log receipt appended last
  and the record cleared *after* every artefact, and a recovery command that
  can itself corrupt state defeats the purpose. The context manager cannot host
  a pre-clear log write, so a manual sequence (or a new helper) is required,
  not a workaround. Date/Author: 2026-06-24, planning agent (revised round 2).
- Decision (**D-LOG**): The recovery entry is appended to `working/log.md` as
  step 3 of the D-SELF sequence — *after* the state edit is applied to the
  in-memory document but *before* the bracket is cleared and the final
  `state.toml` write lands (so the receipt is on disk before the record is
  cleared, satisfying design §3.4 line 237 "appended last as the receipt"
  without re-opening the crash window the round-1 "on clean exit" phrasing
  created). The entry is a single Markdown line (or short block) naming the
  timestamp, the action (`recount`, `complete-pending-turn`,
  `rollback-pending-turn`, or `refuse`), and the discrepancy resolved or
  refused. A `REFUSE` outcome (contradiction or `cursor-plan-present`) appends
  the refusal line but, because no state change is written, does so as a
  single-file append outside the `[pending_turn]` bracket (the state file is
  byte-for-byte unchanged; only `log.md` gains the refusal receipt). Rationale:
  A state repair must leave an audit trail (design §5.4 lines 499-501);
  ordering the receipt before the bracket-clear keeps a torn append from losing
  the receipt while state is already settled. Date/Author: 2026-06-24, planning
  agent (revised round 2).
- Decision (**D-CUPRUM**): All cuprum usage pins to locked `cuprum==0.1.0` and
  reuses the existing `_build_and_install_novel_state` e2e helper
  (`tests/test_novel_state_check.py:304-332`) verbatim: `Program` is a
  `NewType("Program", str)` so an absolute script path is allowlistable
  (`catalogue.py:33-77`; conftest `single_program_catalogue`),
  `sh.make(prog, catalogue=...)` builds the command (`sh.py:529`), and
  `.run_sync(context=ExecutionContext(cwd=dest), capture=True)` returns a
  `CommandResult` with `.exit_code`/`.stdout`/`.stderr` (cached-wheel
  `sh.py:450-455, 89-114`). Do not adopt the drifted dev-checkout
  `output=RunOutputOptions(...)` signature (Surprises & Discoveries).
  Date/Author: 2026-06-24, planning agent.

## Outcomes & retrospective

**Complete (2026-06-24).** All six work items landed, each gated by `make all`
(plus `make markdownlint`/`make nixie` over the touched docs) and a CodeRabbit
pass, committed as one atomic commit per work item. Against the Purpose: a user
runs `novel-state check` on a stale tree and sees the reconciliation reported at
exit `4` (`check` writing nothing), runs `novel-state reconcile` to enact it at
exit `0` with a logged recovery receipt and no `working/` file removed, and a
follow-up `check` is coherent at exit `0` — proven end-to-end by the BDD scenario
(`tests/features/reconcile.feature`) and the wheel-install e2e
(`tests/test_reconcile_e2e.py`). A contradictory or plan-less tree is refused
loudly by both commands at exit `4`, with `reconcile` leaving `state.toml`
byte-for-byte unchanged and logging the refusal. The roadmap's done-claim
headline is delivered as the steady-state stale-`[word_counts]` divergence
(D-SCOPE/D-WORDCOUNT), held sub-threshold so the recount stays
`gate-ratio-consistent`-clean (D-GATES), and the §5.4 worked under-count case is
tested directly. The §5.4 recount-only narrowing is recorded as a gating
design-doc note (D-DESIGN-NOTE).

Deviations from the plan, all recorded above with rationale: D-SCAFFOLD-XFAIL
(the red baseline rendered as a green-gating xfail), D-WC-BY-CHAPTER-ONLY /
D-WC-SHARED-KEYS (the word-count predicate compares the per-chapter mapping over
shared keys only, keeping it orthogonal to `by-chapter-sum` and the bijection),
D-SELF-CONVERGES (an interrupted recount converges in two recovery passes), and
D-CHURN (pre-existing spurious mdformat doc churn set aside via `git stash`). No
Tolerance was breached; no new state field or external dependency was introduced.

## Context and orientation

A newcomer needs these facts before touching code. Read them in this order.

### What exists today

- `novel-state` is a Cyclopts app built by
  `novel_ralph_skill/commands/novel_state.py::build_app()`, exposing `check`,
  `init`, `set-cursor`, `advance-phase`, and `recount`. `build_app()` is
  zero-argument and stable; later tasks import it. `reconcile` is the one
  remaining subcommand to add.
- `check` today is `novel_state.py::_check()`: it loads
  `./working/state.toml`, runs `validate_state` (the eight *pure-state* §5.2
  invariants), and returns a `CommandOutcome` — exit `0` with empty
  `result.violations`, or exit `4` naming the violated invariants. It
  explicitly defers the §5.4 disk-evidence invariants to this task
  (`novel_state.py:23-24`, `validate.py:7-9`).
- The mutators `set-cursor`/`advance-phase` live in
  `novel_ralph_skill/commands/_state_mutators.py`; `recount` lives in
  `novel_ralph_skill/commands/_recount.py`. They share helpers `_state_path`,
  `_working_dir`, `_load_document_or_state_error`, `_state_view_or_state_error`,
  `_refuse_if_incoherent` from `_state_mutators.py`. Reuse these — do not
  duplicate the load/refuse contract.
- The shared contract: a body returns `CommandOutcome(code, result, messages)`
  or raises `StateInputError` (exit `3`); `run`
  (`novel_ralph_skill/contract/runner.py`) owns every `sys.exit` and envelope.
  Exit codes are `ExitCode` (`contract/exit_codes.py`): `0` success, `1` benign,
  `2` usage, `3` state error, `4` actionable finding.
- The typed state model is `novel_ralph_skill/state/` (`State`, `ChapterEntry`,
  `PendingTurn`, etc.). `PendingTurn(operation: str, paths: tuple[str, ...])`
  already exists (`state/schema.py:263-280`) and `parse_state` reads it back
  (`state/__init__.py` re-exports). A settled state has `pending_turn = None`.
- The `tomlkit` round-trip writer is `novel_ralph_skill/state/document.py`:
  `load_document`, `document_to_state`, `write_document_atomically`,
  `open_pending_turn`, `clear_pending_turn`, and the
  `pending_turn(path, operation=…, paths=…)` context manager (the multi-file
  write bracket). The bracket already leaves the populated record on an
  exception and clears it on clean exit; this task is the **consumer** of the
  rollback/complete side.
- `recount_words(working_dir, manifest) -> (current, by_chapter)`
  (`novel_ralph_skill/state/wordcount.py`) is the pure word-count aggregation.
  Reuse it for the stale-`[word_counts]` reconciliation.
- The corpus is `tests/working_corpus/`.
  `_oracle.py::corpus_check(spec, working_dir)` already implements the §5.4
  disk-evidence checks (`_check_manifest_disk_bijection`,
  `_check_done_flag_without_draft`, `_check_compiled_matches_drafts`,
  `_check_pending_turn_cleared`, `_check_cursor_plan_present`) and names them
  via `CORPUS_INVARIANT_NAMES` (`_oracle.py:48-74`). The named incoherent
  variants for each (`done-flag-empty-draft`, `done-flag-absent-draft`,
  `compiled-not-concatenation-of-drafts`, `uncleared-pending-turn`,
  `manifest-extra-entry`, `draft-without-manifest-entry`,
  `scene-cursor-without-plan`, `beat-cursor-without-plan`) live in
  `_variants.py::INCOHERENT_VARIANTS`. Fixtures expose them by name
  (`incoherent_tree`, `incoherent_variant_names`, `check_corpus`,
  `corpus_invariant_names` in `tests/corpus_fixtures.py`).
- Helper builders: `concatenate_drafts`, `draft_body`, `chapter_dir_name`,
  `by_chapter_key`, `derive_by_chapter`, `derive_current` in
  `tests/working_corpus/_specs.py`.

### Terms

- **Pure-state invariant**: a §5.2 rule decidable from `state.toml` alone
  (`validate_state`). **Disk-evidence invariant**: a §5.4 rule needing the
  `working/` tree contents (this task).
- **Reconciliation**: the disk-authoritative state `check` reports and
  `reconcile` writes when state is *behind* coherent disk.
- **Contradiction**: disk that disagrees with itself; refused, never repaired.
- **`[pending_turn]`**: the in-flight multi-file intent record; an uncleared one
  is the signature of a torn turn.

## Interfaces and dependencies

Be prescriptive. By the end of this task these symbols must exist with these
shapes.

In a new module `novel_ralph_skill/state/disk_evidence.py` (the disk-evidence
detector, the §5.4 twin of `validate.py`):

```python
# novel_ralph_skill/state/disk_evidence.py
import typing as typ
from pathlib import Path
from novel_ralph_skill.state.schema import State

MANIFEST_DISK_BIJECTION: typ.Final = "manifest-disk-bijection"
DONE_FLAG_WITHOUT_DRAFT: typ.Final = "done-flag-without-draft"
COMPILED_MATCHES_DRAFTS: typ.Final = "compiled-matches-drafts"
PENDING_TURN_CLEARED: typ.Final = "pending-turn-cleared"
CURSOR_PLAN_PRESENT: typ.Final = "cursor-plan-present"
WORD_COUNTS_MATCH_DRAFTS: typ.Final = "word-counts-match-drafts"  # new (D-WORDCOUNT)

DISK_EVIDENCE_INVARIANT_NAMES: tuple[str, ...] = (...)  # the six, in §5.2/§5.4 order

def check_disk_evidence(state: State, working_dir: Path) -> tuple[Violation, ...]:
    """Return the §5.4 disk-evidence invariants `state` violates against `working_dir`."""
```

Reuse the existing `Violation` dataclass from `validate.py` (re-export it) so
`check` builds one `result.violations` list across both validators.

In a new module `novel_ralph_skill/state/reconcile.py` (the shared derivation):

```python
# novel_ralph_skill/state/reconcile.py
import dataclasses
import enum
from pathlib import Path
from novel_ralph_skill.state.schema import State

class ReconcileAction(enum.StrEnum):
    NONE = "none"                       # coherent; nothing to do
    RECOUNT = "recount"                 # stale [word_counts] vs drafts (D-WORDCOUNT)
    COMPLETE_PENDING_TURN = "complete-pending-turn"   # missing artefacts recomputable (D-COMPLETE)
    ROLLBACK_PENDING_TURN = "rollback-pending-turn"   # an unrecoverable artefact did not land
    REFUSE = "refuse"                   # contradiction OR cursor-plan-present (D-REPORT)

@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class Reconciliation:
    action: ReconcileAction
    discrepancies: tuple[str, ...]      # disk-evidence invariant names that fired
    detail: str                         # human prose for envelope + log
    # action-specific payload:
    #   RECOUNT -> recounted_current: int, recounted_by_chapter: Mapping[str, int]
    #   COMPLETE/ROLLBACK_PENDING_TURN -> operation: str, declared_paths,
    #       missing_paths: tuple[str, ...] (the not-yet-landed declared paths;
    #       all recomputable -> COMPLETE, any unrecoverable -> ROLLBACK)
    #   REFUSE -> the refused discrepancy names (no repair implied)

def derive_reconciliation(state: State, working_dir: Path) -> Reconciliation:
    """Pure: classify the tree as coherent / recountable / pending-turn / refuse.

    Precedence (D-WORDCOUNT, D-REPORT): any contradiction or cursor-plan break
    -> REFUSE; else an uncleared [pending_turn] -> COMPLETE or ROLLBACK per the
    missing declared paths (D-COMPLETE); else word-counts-match-drafts fires ->
    RECOUNT; else NONE. Total: returns a Reconciliation for every State, never
    raises.
    """
```

In `novel_ralph_skill/commands/_reconcile.py` (the mutator body, beside
`_recount.py` to honour the 400-line cap):

```python
def reconcile() -> CommandOutcome:
    """Write the disk-authoritative reconciliation `check` reports; log it; exit 0/4."""
```

In `novel_ralph_skill/commands/novel_state.py`: register a `reconcile`
subcommand in `build_app()` (delegating to `_reconcile.reconcile`), and extend
`_check()` to run `check_disk_evidence` and, when disk-evidence violations
exist, attach the `derive_reconciliation` result to `result["reconciliation"]`
and exit `4`.

No existing signature changes. No new external dependency.

## Plan of work

Stages with go/no-go validation. Do not proceed past a failing stage.

### Work item 0 — Orientation and red baseline (no production code)

Read, in order: design §3.2, §3.3, §3.4, §4.1, §5.2, §5.4; the developers'
guide §"Invariant validation", §"Checker/mutator segregation", §"The
`document.py` round-trip writer"; `state-layout.md` "When state is suspect" and
"Working directory hygiene"; ADR-001 (deterministic/judgemental boundary),
ADR-002 (`tomlkit`), ADR-003 (shared contract). Skim `_oracle.py`,
`_variants.py`, `_recount.py`, `_state_mutators.py`, `document.py`, and
`test_novel_state_check.py`.

Skills to load: `python-router` (then follow it to `python-testing`,
`python-data-shapes`, `python-errors-and-logging`); `leta` for navigation;
`sem` for history.

Write a single failing "scaffold" test `tests/test_reconcile_scaffold.py` that
imports the not-yet-existent `novel_ralph_skill.commands._reconcile.reconcile`
and asserts it is callable — it must fail at import (red baseline). This proves
the suite runs and gives the red→green spine. No production code yet.

Validation: `make test` shows the scaffold test failing with an `ImportError`;
the rest of the suite still passes.

### Work item 1 — Disk-evidence detection module

Create `novel_ralph_skill/state/disk_evidence.py` implementing
`check_disk_evidence(state, working_dir) -> tuple[Violation, ...]` as the §5.4
twin of `validate.py`. Implement one small predicate per name, reusing the
**production** state (`State.chapters`, `State.pending_turn`,
`State.drafting`), and reading the `working/` tree for: chapter-directory
enumeration (the bijection), `done.flag`-vs-`draft.md` per chapter,
`compiled.md`-vs-concatenated- drafts (share a join helper — extract
`concatenate_drafts`'s logic into a small production helper
`novel_ralph_skill.state.compile_model.concatenate_drafts` or reuse the
existing word/draft reader; pin it equal to the corpus helper by test), the
cleared/uncleared `[pending_turn]`, the scene/beat-plan-presence cursor
sub-clause, and — **new this task (D-WORDCOUNT)** — the
`word-counts-match-drafts` predicate. That last predicate recomputes the
per-chapter token counts from the drafts via the shared `recount_words`
(`novel_ralph_skill/state/wordcount.py:86`, which returns
`(current, by_chapter)`; the same `len(text.split())` rule, no second counter),
passing the manifest it derives from `state.chapters`
(`recount_words(working_dir, state.chapters)`), and fires when the recomputed
`by_chapter` or its derived `current` differs from the table — this is the
disk-vs-table signal that realises the roadmap's done-claim case and that the
round-1 plan lacked (round-2 blocking point 2). Its reference twin is **not**
the corpus `live_draft_counts` (`tests/working_corpus/_live_draft.py:69`),
which returns a totals-and-count pair
`(drafted_words_total, drafted_chapters_count)` with **no per-chapter mapping**
and so cannot pin a per-chapter divergence (round-3 blocking point 1). Add a
**new per-chapter disk oracle** to the corpus,
`_check_word_counts_match_drafts` in `tests/working_corpus/_oracle.py`: it globs
`manuscript/chapter-*/draft.md`, splits each present body into the per-chapter
mapping straight from disk, and compares it against the table read from the
materialised `state.toml` (the per-chapter analogue of the existing totals-only
`_check_by_chapter_sum_live`, `_live_draft.py:95`). The corpus predicate reads
**disk**, not the `spec`, because no `WorkingTreeSpec` channel encodes a
per-chapter table-vs-draft divergence (round-2 review advisory 3). Re-export
the **six** name constants and a `DISK_EVIDENCE_INVARIANT_NAMES` tuple from
`novel_ralph_skill/state/__init__.py`, and add `word-counts-match-drafts` to
the corpus oracle's `CORPUS_INVARIANT_NAMES` (wired into `corpus_check` via the
new disk-reading `_check_word_counts_match_drafts`) so the two vocabularies
stay equal.

These predicates are **deliberate twins** of `_oracle.py`'s same-named checks
(the oracle reads the `WorkingTreeSpec`; production reads the materialised
`State` + disk). Add the reciprocal cross-reference comment each module carries
(developers' guide twin policy, lines 371-379). Do not import the oracle.

**Advisory A1 (round-4) — the `manifest-disk-bijection` twin reads the spec,
not disk.** The corpus `_check_manifest_disk_bijection` (`_oracle.py:152-165`)
reads `spec.chapters` / `spec.manifest_only_numbers` and is registered in
`_SPEC_CHECKS` (`_oracle.py:280`), not among the disk-reading checks. So for
the bijection alone the production detector reads disk while its corpus twin
reads the spec; the Work item 3 agreement test still holds because the builder
materialises the spec faithfully, but do **not** "fix" the spec-reading oracle
to read disk and do not describe the bijection twin as "disk-reads-disk" (that
framing is true for `done-flag`, `compiled`, `cursor-plan`, and the new
`word-counts-match-drafts` twins, which both read disk). Pin the production
bijection detector to the existing spec-reading oracle as-is.

Documentation to read: design §5.4; developers' guide §"Invariant validation"
(the twin policy and disk-evidence list). Skills: `python-router` →
`python-data-shapes`, `python-errors-and-logging`,
`python-iterators-and-generators`.

Tests (`tests/test_disk_evidence.py`):

- Unit: each predicate fires on its matching `INCOHERENT_VARIANTS` tree and is
  silent on `COHERENT_BASELINE` and the `PHASE_STATES`/`DONE_FLAG_PERMUTATIONS`
  coherent trees (drive via `incoherent_tree`, `baseline_tree`,
  `done_flag_tree` fixtures).
- Pin: `DISK_EVIDENCE_INVARIANT_NAMES` (now six names) equals the corpus
  oracle's disk-evidence subset of `CORPUS_INVARIANT_NAMES` (via
  `corpus_invariant_names` fixture), including the newly added
  `word-counts-match-drafts`.
- A `compiled.md` join-helper equality test: the production concatenation equals
  `concatenate_drafts` (corpus) byte-for-byte on the present drafts.
- A `word-counts-match-drafts` twin-equality test: the production predicate's
  per-chapter verdict equals the new disk-reading corpus oracle
  `_check_word_counts_match_drafts` (built on the draft glob-and-split, **not**
  `live_draft_counts`, which has no per-chapter mapping — round-3 blocking point
  1) on every corpus tree (coherent, every `INCOHERENT_VARIANTS` member,
     **both**
  word-count variants — `done-claim-stale-word-counts` over-count and
  `done-flag-real-draft-undercount` under-count), so the disk-vs-table detector
  is pinned to the independent oracle. Both sides read disk, so the test
  compares like with like (round-2 review advisory 3).

Add a **second** word-count corpus variant in this work item,
`done-flag-real-draft-undercount` — the genuine §5.4 worked case (round-4
blocking point B2). It is a **settled** tree whose first chapter carries a real
`done.flag` over a **non-empty** draft (`has_done_flag=True`, `draft_words>0`,
`write_draft=True`) but whose `by_chapter_override` **under-counts** that
chapter (a positive table entry smaller than the drafted token count), with
`current_words_override` left consistent so `by-chapter-sum` stays satisfied.
Build it **strictly sub-threshold** (D-GATES): the under-count delta must move
the `sum(by_chapter)/target` ratio across **no** 30/50/80% boundary, so honest
gates hold for both the table total and the recounted draft total. Because the
`done-flag-without-draft` predicate fires only on `draft_words == 0`
(`_oracle.py:206-215`), a `done.flag` over a non-empty draft does **not** trip
the contradiction; the tree's sole disk-evidence violation is
`word-counts-match- drafts` → `RECOUNT`. Register it in `INCOHERENT_VARIANTS` as
`(spec, oracle.WORD_COUNTS_MATCH_DRAFTS)` and add a sole-violation assertion
(as for the over-count variant). This is the design's actual §5.4 worked
example — "state claims a chapter is not done but a `done.flag` exists" with
the table behind disk — not the inverse the round-3 variant chose. The advisory
A1 note (below) applies to the bijection twin, not to this variant.

Validation: `make test` green for the new module;
`make lint typecheck check-fmt` clean.

### Work item 2 — The shared `derive_reconciliation` pure function

Create `novel_ralph_skill/state/reconcile.py` with `ReconcileAction`,
`Reconciliation`, and `derive_reconciliation(state, working_dir)`.
Classification logic (pure, no writes):

1. Run `check_disk_evidence` and `validate_state`. Partition the disk-evidence
   violations into three classes: **refuse-class** — the three contradictions
   (`manifest-disk-bijection`, `done-flag-without-draft`,
   `compiled-matches- drafts`) *and* `cursor-plan-present`
   (reported-not-repaired, D-REPORT); **pending-turn** —
   `pending-turn-cleared`; **recountable** — `word-counts-match-drafts`.
2. If any refuse-class violation is present → `action = REFUSE`, `discrepancies`
   = those names (D-REPORT). This is the single fourth action both
   contradictions and `cursor-plan-present` map to, so no disk-evidence
   violation can fall through to `NONE` while `check` exits 4 (round-2 blocking
   point 4 closed).
3. Else if `pending-turn-cleared` fires (uncleared `[pending_turn]`) → read the
   record's `paths`, compute the **missing** declared paths (declared but not
   on disk), and choose by D-COMPLETE: if every missing path is recomputable
   (`state.toml` / `log.md`) → `COMPLETE_PENDING_TURN`, carrying the
   missing-path set and the operation; if any missing path is unrecoverable (a
   `draft.md`, a `done.flag`) → `ROLLBACK_PENDING_TURN`. (When nothing is
   missing, the record is a stale marker over a fully-landed turn →
   `COMPLETE_PENDING_TURN` with an empty missing set: the dispatch simply
   clears the record.)
4. Else if `word-counts-match-drafts` fires → the recount payload is already the
   disk-derived `current`/`by_chapter` from step 1's predicate;
   `action = RECOUNT` carrying them.
5. Else → `action = NONE`.

`cursor-plan-present` is resolved here, not deferred: it is reported by `check`
(exit 4) and maps to `REFUSE` for `reconcile` (D-REPORT), because `reconcile`
cannot synthesise a missing plan from disk without fabricating prose. No
classification is left "escalate if ambiguous"; the precedence above is total
and the property test below pins it.

Documentation: design §5.4 (the complete/rollback split, lines 502-510; the
refuse rule, lines 512-519). Skills: `python-router` → `python-data-shapes`,
`python-abstractions` (for the action enum dispatch).

Tests (`tests/test_reconcile_derivation.py`):

- Unit: each corpus variant maps to the expected `ReconcileAction` (table-driven
  over `INCOHERENT_VARIANTS` plus the three new Work-item-4 specs —
  `done-claim-stale-word-counts` → `RECOUNT`,
  `pending-turn-complete-recomputable` → `COMPLETE_PENDING_TURN`,
  `pending-turn-rollback-unrecoverable` → `ROLLBACK_PENDING_TURN`;
  `scene-cursor-without-plan` / `beat-cursor-without-plan` → `REFUSE`; coherent
  trees → `NONE`).
- Property (`hypothesis`): `derive_reconciliation` is **total** — it returns a
  `Reconciliation` (never raises) for every constructible `State` over a
  materialised tree; and the precedence is deterministic and exhaustive: a
  refuse-class violation dominates a pending-turn signal, which dominates
  `word-counts-match-drafts`, which dominates `NONE`, and **no** disk-evidence
  violation ever yields `NONE` (the round-2 blocking-point-4 invariant). Load
  the `hypothesis` skill; gate per `python-verification` that example-based
  tests are insufficient for the precedence invariant (a range of violation
  combinations), justifying the property test.

Validation: `make test` green; `make lint typecheck check-fmt` clean.

### Work item 3 — Wire disk-evidence detection into `check`

Extend `novel_state.py::_check()` to: load the state, run `validate_state` (as
now) **and** `check_disk_evidence(state, working_dir)`, and union the
violations into `result["violations"]`. When any disk-evidence violation is
present, call `derive_reconciliation` and attach its rendered form to
`result["reconciliation"]` (action + discrepancies + detail), exiting `4`.
`check` writes nothing. Keep the exit-`3` channel for missing/unparseable state.

Add the corpus-agreement test (Work item 3's headline), mirroring
`test_validate_state_corpus.py::test_incoherent_agreement_restricted_to_owned`:
for every coherent corpus tree and every `INCOHERENT_VARIANTS` member, the
production union detector (`validate_state` ∪ `check_disk_evidence`) returns
exactly the oracle's `corpus_check` verdict, restricted to the full
`CORPUS_INVARIANT_NAMES` vocabulary. This is the safety net pinning the twin
predicates.

Documentation: design §4.1 (the `check` row), §5.2, §5.4; developers' guide
§"Invariant validation". Skills: `python-router` → `python-testing`.

Tests (extend `tests/test_novel_state_check.py` and add
`tests/test_novel_state_check_disk.py` if the file nears 400 lines):

- Behavioural: a `done-claim-stale-word-counts` / `uncleared-pending-turn` /
  `done-flag-empty-draft` / `manifest-extra-entry` /
  `scene-cursor-without-plan` tree exits `4` with the expected name in
  `result.violations` and a `result.reconciliation` describing the action
  (`recount` / `rollback`-or-`complete` / `refuse`).
- The strengthened `test_check_writes_nothing` covering the disk-evidence path
  (byte-for-byte tree unchanged after a disk-evidence exit-`4`).
- The whole-corpus agreement test above.
- Snapshot (`syrupy`): the machine envelope for the headline stale tree
  (`done-claim-stale-word-counts`, action `recount`) and one refuse-class tree
  (`done-flag-empty-draft`, action `refuse`), with timestamps/paths redacted.
  Pair each snapshot with a semantic assertion on the action name (AGENTS.md
  snapshot rules — no snapshot-only coverage).

Validation: `make test` green; `make lint typecheck check-fmt` clean.

### Work item 4 — `reconcile` mutator (recount + pending-turn recovery)

Create `novel_ralph_skill/commands/_reconcile.py::reconcile()` and register it
in `build_app()`. The body:

1. `_state_path()` / `_working_dir()` (reuse `_state_mutators` helpers); load
   the document via `_load_document_or_state_error`; derive the typed view via
   `_state_view_or_state_error` (both already route faults to exit `3`).
2. `derive_reconciliation(state, working_dir)` (independent recompute —
   D-SHARED).
3. Dispatch on `action`. The repairs that write state (`RECOUNT`,
   `COMPLETE_PENDING_TURN`, `ROLLBACK_PENDING_TURN`) all run through the
   **manual bracket sequence** of D-SELF — `open_pending_turn` + write, then
   the state edit, then the `log.md` append, then `clear_pending_turn` + write
   — never the `pending_turn` context manager (which clears on `__exit__` with
   no pre-clear log hook; round-2 blocking point 5). A helper
   `run_reconcile_bracket(path, *, edit, log_line)` encapsulates steps 1-4 in
   that fixed order so each action body just supplies its `edit` closure and
   log line.
   - `NONE` → exit `0`, empty action, no write, no log (no bracket).
   - `RECOUNT` → `edit` rewrites `[word_counts]` exactly as `_recount` does
     (fresh
     ordered inline `by_chapter`, `current = sum(by_chapter)`) and
     `_refuse_if_incoherent` validates the proposed document before the final
     write; `log_line` names `recount` and the discrepancy. Exit `0` reporting the
     written counts.
   - `COMPLETE_PENDING_TURN` → `edit` writes each **recomputable** missing
     declared path (per D-COMPLETE: re-derive `[word_counts]` if `state.toml` is
     a missing declared path; the `log.md` receipt is itself one of the remaining
     artefacts and is written by the bracket's own step 3) and then
     `clear_pending_turn`. It never writes a `draft.md`/`done.flag` (those force
     `ROLLBACK` in `derive_reconciliation`). `log_line` names
     `complete-pending-turn`. Exit `0`.
   - `ROLLBACK_PENDING_TURN` → `edit` is `clear_pending_turn` only; all
     `working/`
     artefacts stay in place (delete nothing). `log_line` names
     `rollback-pending-turn`. Exit `0`.
   - `REFUSE` → no `[pending_turn]` bracket and **no** state change; append a
     single `refuse` receipt line to `log.md` (a lone single-file append, D-LOG),
     exit `4` (covers contradictions and `cursor-plan-present`; handled fully in
     Work item 5).
4. Success `result` is **write-shaped** (names the action and what changed),
   never `check`'s `violations` read shape (developers' guide lines 287-289;
   audit-2.2.2 Finding 2).

Implement the `log.md` append via a small
`_append_recovery_entry(working_dir, line)` helper (append mode, UTF-8). The
bracket helper calls it as step 3 (before the clear-and-write), so the receipt
is on disk before the record clears (D-LOG). Keep the file under 400 lines; if
the dispatch table grows, split the per-action bodies into a small
`_reconcile_actions.py`.

Documentation: design §3.4, §4.1, §5.4; developers' guide §"Checker/mutator
segregation" (the multi-file bracket), §"The `document.py` round-trip writer".
Skills: `python-router` → `python-errors-and-logging`, `python-abstractions`.

Tests (`tests/test_reconcile.py`, plus a BDD scenario):

- Add to the corpus (`tests/working_corpus/_variants.py`) the roadmap's
  **headline** variant `done-claim-stale-word-counts`: a **settled** tree (no
  `[pending_turn]`) whose `word_counts.by_chapter` table claims a done chapter
  the on-disk drafts do not corroborate. Build it **precisely** so that
  `word-counts-match-drafts` is its **sole** violation (round-3 blocking point
  2): take the first baseline chapter and set, on its `ChapterSpec`,
  `draft_words=0`, `write_draft=False`, and **`has_done_flag=False`**, then set
  the `WorkingTreeSpec` `by_chapter_override` so that chapter's table entry is
  **positive** (the "done claim") while every other entry derives from the
  drafts (and set `current_words_override`/leave it `None` so
  `current == sum(by_chapter_override)` keeps the table-internal
  `by-chapter-sum` invariant satisfied — only the disk-vs-table predicate must
  fire, never the table-internal one). The phantom positive entry must be
  **strictly sub-threshold** (D-GATES, round-4 blocking point B1): choose its
  magnitude so removing it (the recount drops the table total to the draft
  total) moves the `sum(by_chapter)/target` ratio across **no** 30/50/80%
  boundary, so the honest gates `_consistent_gates` (`_variants.py:36-40`)
  writes from the **draft** total stay consistent with both the pre-repair
  **table** total and the post-repair recounted total. This keeps
  `gate-ratio-consistent` (`validate.py:247-275`) silent before *and* after the
  recount — without it the stale tree would also fire `gate-ratio-consistent`
  (failing the sole-violation guard) or the post-repair `check` would exit `4`
  (defeating "check then exits 0"). The `has_done_flag=False` is
  **load-bearing**: if the chapter inherited `has_done_flag=True` from `_BASE`
  (as `done-flag-empty-draft` does, `_variants.py:63`), the tree would also
  trip the `done-flag-without-draft` *contradiction*, which by precedence
  (refuse dominates recount) maps to `REFUSE` → `reconcile` exit `4`, defeating
  the roadmap headline's "repaired by reconcile" (`docs/roadmap.md:651-652`).
  With `has_done_flag=False` the directory holds a positive table entry over an
  absent/empty draft and no `done.flag`, so **only** `word-counts-match-drafts`
  fires and the action is `RECOUNT` (exit `0` repair). This is exactly the
  roadmap clause's "state claims a chapter is done **but no `done.flag`
  exists**". This is the steady-state divergence the roadmap names (D-SCOPE);
  it is *not* a `[pending_turn]` case. Register the variant in
  `INCOHERENT_VARIANTS` as `(spec, oracle.WORD_COUNTS_MATCH_DRAFTS)` and wire
  fixture access through the existing `incoherent_tree`/builder pattern.
- **Sole-violation assertion** for the headline variant (the corpus single-
  invariant self-test, mirroring `INCOHERENT_VARIANTS`'s isolation contract): a
  test asserts `corpus_check(spec, working_dir)` for
  `done-claim-stale-word-counts` returns **exactly**
  `("word-counts-match-drafts",)` — neither `done-flag-without-draft` nor
  `by-chapter-sum` nor any other name — so the variant cannot silently regress
  into a `REFUSE` tree (round-3 blocking point 2 regression guard).
- Add the two **pending-turn** variants for the complete/rollback split
  (`pending-turn-complete-recomputable`: an uncleared record whose only missing
  declared path is `state.toml`/`log.md`;
  `pending-turn-rollback-unrecoverable`: an uncleared record whose missing
  declared path is a `draft.md`/`done.flag`), realising D-COMPLETE.
- Behavioural (**roadmap headline**): the `done-claim-stale-word-counts` tree →
  `check` exits `4` naming `word-counts-match-drafts` with a `recount`
  reconciliation; `reconcile` exits `0`, rewrites `[word_counts]` to the
  disk-derived values, appends a `recount` recovery entry to `working/log.md`,
  removes no file; a follow-up `check` exits `0`. This is the literal
  `docs/roadmap.md:651-652` success clause.
- **Post-repair gate-clean assertion (round-4 blocking point B1).** For **both**
  word-count variants (`done-claim-stale-word-counts` over-count and
  `done-flag-real-draft-undercount` under-count): after `reconcile` runs
  `RECOUNT`, re-load the written `state.toml` and assert `validate_state`
  returns **no** `gate-ratio-consistent` violation — the reconciled tree is
  gate-clean — and the follow-up `check` exits `0`. This is the direct B1
  regression guard that a `[word_counts]`-only recount left the gates coherent
  (true only because the variants are sub-threshold by construction, D-GATES).
  Pair it with a negative fixture: a *threshold-crossing* over-count tree's
  `RECOUNT` would leave `gate-ratio-consistent` failing — assert that
  `reconcile` on such a tree does **not** silently produce a clean exit-`0` (it
  surfaces the gate conflict; the `recount`-style `_refuse_if_incoherent`
  backstop or the Tolerance escalation applies), documenting the scope boundary
  rather than mis-repairing.
- **Behavioural (§5.4 worked case, round-4 blocking point B2):** the
  `done-flag-real-draft-undercount` tree → `check` exits `4` naming
  `word-counts-match-drafts` with a `recount` reconciliation; `reconcile` exits
  `0`, rewrites `[word_counts]` so the under-counted chapter's table entry
  matches its real drafted token count, appends a `recount` recovery entry,
  removes no file; a follow-up `check` exits `0` and is
  `gate-ratio-consistent`-clean. This exercises the design's actual §5.4 worked
  example (a real `done.flag` over a non-empty draft the table is behind), not
  merely the round-3 inverse.
- Behavioural: the rollback tree → `reconcile` clears `[pending_turn]`, leaves
  every `working/` file present (subset-before-after assertion — Constraint "no
  deletion"), logs `rollback-pending-turn`, exits `0`; a follow-up `check` exits
  `0`.
- Behavioural: the complete tree → `reconcile` clears the record (artefacts
  verified present), logs `complete-pending-turn`, exits `0`.
- The headline `tests/features/reconcile.feature` scenario: "stale tree detected
  by check at 4, repaired by reconcile, re-checked clean" (steps in
  `tests/steps/reconcile_steps.py`, bound by `tests/test_reconcile_bdd.py`,
  mirroring `recount`/`torn_turn` wiring).

Validation: `make test` green; `make lint typecheck check-fmt` clean.

### Work item 5 — Contradiction refusal in both commands

Finalise the `REFUSE` path (D-REPORT — the single action for both
contradictions and `cursor-plan-present`): in `check`, a refuse-class tree exits
`4` with the refused names in `result.violations` and a
`result.reconciliation` of action `refuse` (no repair implied). In `reconcile`,
a refuse-class tree exits `4`, appends a `refuse` entry to `log.md`, and writes
**no** state change (the state file is byte-for-byte unchanged; only `log.md`
gains the refusal receipt). Cover all three contradiction classes —
`done-flag-without-draft` (empty *and* absent draft variants),
`compiled-matches-drafts` (the `compiled-not-concatenation-of-drafts` variant,
modelling a compile referencing absent content), and `manifest-disk-bijection`
(`manifest-extra-entry`, `draft-without-manifest-entry`) — **and** the
`cursor-plan-present` class (the `scene-cursor-without-plan` and
`beat-cursor-without-plan` variants), proving the round-2 control-flow fork is
closed: a `scene-cursor-without-plan` tree exits `4` in both commands and never
produces a `NONE` reconciliation while exiting `4`.

Documentation: design §5.4 lines 512-519 ("refuses to repair … reports the
conflict … logs it … exits 4"). Skills: `python-router` →
`python-errors-and-logging`.

Tests (extend `tests/test_reconcile.py`):

- Each refuse-class variant (three contradiction classes **and**
  `scene-cursor-without-plan` / `beat-cursor-without-plan`) → both `check` and
  `reconcile` exit `4` with action `refuse`.
- `reconcile` on a refuse-class tree leaves `state.toml` byte-for-byte unchanged
  but appends a `refuse` line to `log.md`.
- A `scene-cursor-without-plan` tree specifically: `check`'s exit-4 payload
  carries a `refuse` reconciliation (never `none`), and `reconcile` exits `4`
  (never `0`) — the round-2 blocking-point-4 regression guard.
- A snapshot of the refuse envelope (paired with a semantic action assertion).

Validation: `make test` green; `make lint typecheck check-fmt` clean.

### Work item 6 — Cross-check, idempotence, self-recovery, e2e, docs

- **`check`/`reconcile` cross-check** (`tests/test_reconcile.py`): for every
  corpus tree (coherent, every `INCOHERENT_VARIANTS` member, and the four new
  variants — `done-claim-stale-word-counts`, `done-flag-real-draft-undercount`,
  `pending-turn-complete-recomputable`, `pending-turn-rollback-unrecoverable`),
  the `ReconcileAction` `check` reports equals the action `reconcile` enacts
  (drive both, compare). This pins D-SHARED, and — because
  `cursor-plan-present` and contradictions both map to `REFUSE` (exit 4) and
  never to `NONE` (exit 0) — it is internally consistent with the idempotence
  test below (round-2 blocking point 4).
- **Idempotence**: a second `reconcile` over an already-reconciled tree is a
  no-op (action `NONE`, exit `0`, `state.toml` byte-for-byte unchanged). A
  second `check` exits `0`. Because only a genuinely coherent tree yields
  `NONE` (a refuse-class tree always yields `REFUSE`/exit 4),
  `NONE`-means-exit- 0 holds without contradicting the exit-4 paths.
- **Self-recovery** (D-SELF): simulate an interrupted `reconcile` by raising
  between steps of the manual bracket (after `open_pending_turn`+write, before
  the final `clear_pending_turn`+write — the seam `torn_turn_steps.py` already
  exercises for producers) and assert the populated `[pending_turn]` for
  `operation="reconcile"` is left on disk **and** that an interruption *after*
  the log append but *before* the bracket clear still leaves a recoverable
  record (the receipt-loss window the round-1 plan opened is closed); a
  subsequent `reconcile` re-derives and finishes it.
- **e2e** (POSIX-only, ADR-006): reuse `_build_and_install_novel_state` verbatim
  (D-CUPRUM); build+install the wheel, materialise a stale tree under the
  subprocess cwd, run the installed `novel-state reconcile` via
  `sh.make(prog, catalogue=single_program_catalogue(...))` invoked with
  `("reconcile")` then
  `.run_sync(context=ExecutionContext(cwd=dest), capture=True)`, assert
  `exit_code == 0` and a coherent follow-up `check`. Mark `@pytest.mark.slow`,
  `@pytest.mark.timeout(180)`, `@pytest.mark.skipif(os.name != "posix", ...)`.
- **Documentation**: update `docs/developers-guide.md` §"Invariant validation"
  to reclassify the disk-evidence set as **six** invariants, not five
  (`developers-guide.md:309-314` currently names exactly five "task 2.3.2's");
  the five reserved names plus the new `word-counts-match-drafts` are now
  *implemented* by `check_disk_evidence`, and the guide's "no live analogue"
  note on `by-chapter-sum` (`developers-guide.md:366-367`) should reference the
  new disk-vs-table predicate that now fills that gap (round-2 review advisory
  2). Extend `test_owned_names_equal_corpus_vocabulary` (not merely mention it)
  so it pins the six-name disk-evidence vocabulary across the production module
  and the corpus oracle. Also update §"The five commands" / §"Checker/mutator
  segregation" (reconcile is now the first multi-file mutator, with the
  `pending_turn` bracket); update `docs/users-guide.md` for the new `reconcile`
  subcommand and the disk-aware `check` (the recovery routine is now a
  command). Record the D-LOG append-ordering deviation from design §3.4 line
  237 ("log entry appended last") as an explicit design note in
  `docs/developers-guide.md` (the receipt is written before the final
  bracket-clear+`state.toml` write to close the receipt- loss window, justified
  by §3.4 lines 243-245; round-2 review advisory 1) rather than leaving it only
  in this plan's Decision Log.
- **§5.4 design-doc note (gating, D-DESIGN-NOTE; round-4 blocking point B2).**
  Add a note to `docs/novel-ralph-harness-design.md` §5.4 — and an ADR
  referenced from the design document if the reviewer judges the decision
  substantive (AGENTS.md "Project documentation", lines 181-183) — recording
  that v1's disk-authoritative `reconcile` repairs (i) stale `[word_counts]` vs
  the drafts (sub-threshold only; gates are not re-derived because a gate flag
  records the agent's "integrated and logged" act disk does not store —
  D-GATES) and (ii) an uncleared `[pending_turn]`, and that the broader
  `done.flag`/`compiled.md`-driven reconstruction §5.4 lines 489-492 describes
  (a per-chapter done projection, gate re-projection) is **deferred** to a
  later task. The note also records the A2 interpretation that
  `cursor-plan-present` (the §5.2 invariant-6 sub-clause) is given §5.4
  `REFUSE` semantics. **This note is a required deliverable that lands with (or
  before) the headline code** — not a conditional "only if a design-level
  decision needs recording" item; re-deriving §5.4's reconstruction down to a
  recount *is* the design-level decision, so it must be signed off in the
  design document, not only this plan's Decision Log. Run `make markdownlint`
  and `make nixie` over the edited design doc. Update `docs/roadmap.md` to mark
  2.3.2 done at the end.

Documentation: AGENTS.md "Documentation maintenance";
`docs/documentation-style- guide.md`; the e2e ADR-006. Skills: `python-router` →
`python-testing`; `en-gb-oxendict` for all prose.

Validation: `make all`; for the Markdown changes, additionally
`make markdownlint` and `make nixie`.

## Concrete steps

All commands run from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-3-2`.

1. Confirm the branch and a clean tree:

   ```console
   $ git branch --show-current
   roadmap-2-3-2
   ```

2. Work item 0 red baseline, then per item: run the targeted suite first, then
   the full gate. Prefer Makefile targets; do not run gates in parallel (shared
   Cargo/uv cache and build caching — global instructions).

   ```bash
   make test           # red baseline / per-item green
   make all            # build + check-fmt + lint + typecheck + test
   ```

3. After any `.md` change:

   ```bash
   make fmt            # formats Markdown and fixes table markup
   make markdownlint
   make nixie          # validates any Mermaid diagrams
   ```

4. Commit each work item separately, gated, with an imperative en-GB subject
   (~50 chars) and a wrapped body explaining what and why. Branch is already
   `roadmap-2-3-2`; do not commit to `main`.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes. New tests that must exist and pass:
  `tests/test_disk_evidence.py`, `tests/test_reconcile_derivation.py`,
  `tests/test_reconcile.py`, the corpus-agreement test, the
  `tests/features/reconcile.feature` BDD scenario, the snapshots, the property
  test, and the POSIX e2e. Each headline behavioural test must **fail before**
  the matching production change and **pass after** (red→green).
- Lint/format/typecheck: `make lint`, `make check-fmt`, `make typecheck` clean;
  100% `interrogate` docstring coverage; Pylint clean.
- Audit: `make audit` clean (no new dependency).
- Markdown: `make markdownlint` and `make nixie` clean for all `.md` edits.

Quality method (how we check): `make all` is the single command gating code
work; the two Markdown commands gate documentation. Behaviour is observable
through the BDD scenario and the e2e: a user runs `novel-state check` on a
stale tree (exit `4`, reconciliation reported), `novel-state reconcile` (exit
`0`, `log.md` gains a recovery entry, no `working/` file removed), and
`novel-state check` again (exit `0`); a contradiction tree is refused by both
at exit `4`.

Acceptance phrased as behaviour:

- "Running `make test` passes;
  `tests/test_reconcile.py::test_done_claim_stale_word_counts_detected_and_repaired`
  fails before the change and passes after."
- "(Roadmap headline, `docs/roadmap.md:651-652`) A settled `working/` tree whose
  `state.toml` claims a chapter is done — a positive `word_counts.by_chapter`
  entry the on-disk drafts do not corroborate, with no `done.flag` — is
  detected by `novel-state check` at exit `4` naming `word-counts-match-drafts`
  with a `recount` reconciliation; `novel-state reconcile` exits `0`, rewrites
  `[word_counts]` to the disk-derived values, removes no file, and appends a
  `recount` recovery entry to `working/log.md`; `check` then exits `0`, while
  `check` itself wrote nothing throughout. The reconciled `state.toml` is
  `gate-ratio-consistent`-clean (the variant is sub-threshold; D-GATES), so the
  follow-up `check` does not re-fire a fresh finding (round-4 blocking point
  B1)."
- "(§5.4 worked case, round-4 blocking point B2) A settled `working/` tree whose
  first chapter carries a real `done.flag` over a **non-empty** draft the
  `word_counts.by_chapter` table **under-counts** is detected by
  `novel-state check` at exit `4` naming `word-counts-match-drafts` (never the
  `done-flag-without-draft` contradiction, which fires only over an empty
  draft) with a `recount` reconciliation; `novel-state reconcile` exits `0`,
  rewrites `[word_counts]` to the disk-derived values, and a follow-up `check`
  exits `0` and is gate-clean — exercising the design's actual §5.4
  reconstruction direction."
- "(Scope boundary, D-GATES) A done-claim divergence whose recounted total would
  cross a knitting-gate threshold the recorded gates do not reflect is **not**
  silently repaired: `reconcile` surfaces the gate conflict rather than
  fabricating the `[gates]` flag, honouring 'disk authoritative, never the
  reverse'."
- "(Design sign-off, D-DESIGN-NOTE) `docs/novel-ralph-harness-design.md` §5.4
  carries a note recording the v1 recount-only reconciliation scope and the
  deferred `done.flag`/`compiled.md` reconstruction, landing with the headline
  code; `make markdownlint` and `make nixie` pass over it."
- "A `working/` tree whose `state.toml` left an uncleared `[pending_turn]` whose
  missing declared path is a `draft.md`: `novel-state check` exits `4` naming
  `pending-turn-cleared` with a `rollback-pending-turn` reconciliation;
  `novel-state reconcile` exits `0`, clears the record, removes no file, and
  appends a recovery entry to `working/log.md`; a follow-up `check` exits `0`."
- "A `done.flag` beside an empty `draft.md`, or a non-zero scene cursor with no
  `scenes.md`: both `novel-state check` and `novel-state reconcile` exit `4`;
  `reconcile` leaves `state.toml` byte-for-byte unchanged and appends a
  `refuse` entry to `log.md`."

## Idempotence and recovery

- Every gate is re-runnable. `make all` is safe to repeat.
- `reconcile` is idempotent: a second run over an already-reconciled tree is a
  no-op (action `NONE`, no write). The Work item 6 idempotence test pins this.
- `reconcile`'s own writes are atomic (`write_document_atomically`) and
  bracketed (`pending_turn`), so an interrupted reconcile leaves either the
  prior coherent state or a recoverable `[pending_turn]` record — never a
  half-written file.
- If a work item's gate fails, fix forward within the iteration tolerance (5
  attempts); on breach, stop and escalate per Tolerances. No destructive steps
  are involved; `working/` deletion is forbidden by Constraint.

## Artifacts and notes

- Locked-cuprum pin evidence (D-CUPRUM): cached wheel
  `~/.cache/uv/archive-v0/vvzZ1jTMbiIrGZD_2Lryn/cuprum/sh.py:450-455`
  (`run_sync(*, capture=True, echo=False, context=None)`), `:89-114`
  (`CommandResult.exit_code/stdout/stderr`), `:529`
  (`make(program, *, catalogue=DEFAULT_CATALOGUE)`); `catalogue.py:33-77`
  (`ProjectSettings`/`ProgramCatalogue`, allowlist gate); `program.py:16`
  (`Program = NewType("Program", str)`). The existing passing e2e helper using
  exactly this shape is `tests/test_novel_state_check.py:304-371`.
- Corpus disk-evidence model to mirror:
  `tests/working_corpus/_oracle.py:152-267` (the five disk-evidence predicates)
  and `:288-313` (`corpus_check`).
- The `[pending_turn]` producer/consumer seam:
  `novel_ralph_skill/state/document.py:154-243`.

## Revision note

Initial draft (2026-06-24). Scoped `reconcile`'s repairs to `[pending_turn]`
recovery and stale `[word_counts]`, pinned cuprum to locked 0.1.0, and reused
the reserved disk-evidence names and the corpus oracle as the independent twin.

Revision 2 (2026-06-24, round-2 design review). Resolved all five blocking
points:

1. **Steady-state done-claim (blocking point 1).** D-SCOPE rewritten: the
   roadmap headline is the *settled* stale-`[word_counts]` divergence, **not**
   a pending-turn rollback. Done-ness lives in `word_counts.by_chapter`
   (`schema.py:228-260`); the §5.4 lines 489-492 worked direction reconstructs
   it from disk. Delivered by the new `done-claim-stale-word-counts` variant
   and the `RECOUNT` repair (Purpose, D-SCOPE, Work items 1/2/4, acceptance).
2. **Missing detection signal (blocking point 2).** Added the disk-evidence
   invariant `word-counts-match-drafts` (D-WORDCOUNT), a genuine disk-vs-table
   word-count predicate built on the shared `recount_words`. (Round 3 corrected
   the twin: the per-chapter predicate is pinned to a **new per-chapter disk
   oracle**, not the totals-only `live_draft_counts` — see the round-3 note
   below.) This closes the gap that the table-internal `by-chapter-sum` ("no
   live analogue") left. Recount is fired *only* by this detector, not
   unconditionally, so it does not poach the `recount` command's role.
3. **COMPLETE that never wrote (blocking point 3).** D-COMPLETE:
   `COMPLETE_ PENDING_TURN` is selected when every *missing* declared artefact
   is recomputable (`state.toml`/`log.md`) and `reconcile` then writes those
   recomputable artefacts; an unrecoverable missing artefact (`draft.md`/
   `done.flag`) forces `ROLLBACK`. "Completing writes the remaining artefacts"
   is now literally true and never fabricates prose.
4. **cursor-plan-present control-flow fork (blocking point 4).** D-REPORT: the
   action enum's fourth member is `REFUSE` (not `REFUSE_CONTRADICTION`), and
   `cursor-plan-present` maps to it alongside contradictions. No disk-evidence
   violation falls through to `NONE`; the cross-check and the
   `NONE`-means-exit- 0 idempotence test are mutually consistent. Property test
   asserts no violation yields `NONE`.
5. **Unrecoverable log-receipt window (blocking point 5).** D-SELF/D-LOG:
   reconcile abandons the `pending_turn` context manager and drives the
   lower-level seam manually — `open_pending_turn`+write, state edit, `log.md`
   append, `clear_pending_turn`+write — so the receipt lands *before* the
   bracket clears. An interrupt at any step leaves a recoverable
   `operation="reconcile"` record.

No remaining undecided forks: both round-1 scope questions are resolved against
the design (§5.4) and the corpus, not deferred to a tolerance.

Revision 3 (2026-06-24, round-3 design review). Resolved both blocking points:

1. **Wrong `word-counts-match-drafts` twin (blocking point 1).** The plan named
   the corpus `live_draft_counts` (`_live_draft.py:69`) as the twin, but that
   helper returns only `(drafted_words_total, drafted_chapters_count)` — a
   total and a chapter *count*, with **no per-chapter mapping** — so a
   per-chapter divergence cannot be pinned equal to it. Re-specified the twin
   against a **per-chapter reference**: production reads disk via
   `recount_words` (`wordcount.py:86`, returning `(current, by_chapter)`),
   passing the manifest it derives from `state.chapters`; the corpus side adds
   a **new disk-reading oracle** `_check_word_counts_match_drafts` in
   `_oracle.py` that globs `manuscript/chapter-*/draft.md`, splits each present
   body into a per-chapter mapping straight from disk, and compares it against
   the table read from the materialised `state.toml` (the per-chapter analogue
   of `_check_by_chapter_sum_ live`). The pinning test now compares two
   **per-chapter, disk-reading** verdicts — like with like (also closing
   round-2 review advisory 3). Corrected in the Controlling-decision section,
   D-WORDCOUNT, Work item 1 (spec + twin- equality test), and the Risks
   mitigation.
2. **Headline variant self-defeat via `done-flag-without-draft` (blocking point
   2).** The `done-claim-stale-word-counts` variant was silent on `done.flag`;
   if it inherited `has_done_flag=True` from `_BASE` it would trip the
   `done-flag-without-draft` contradiction → `REFUSE` → `reconcile` exit `4`,
   failing the roadmap headline's "repaired by reconcile". Work item 4 now pins
   the variant explicitly: the first chapter carries `draft_words=0`,
   `write_draft=False`, and **`has_done_flag=False`**, with a positive
   `by_chapter_override` table entry (`current` left consistent so
   `by-chapter- sum` still holds), so **only** `word-counts-match-drafts` fires
   and the action is `RECOUNT` (exit `0`). Added a sole-violation assertion that
   `corpus_check(spec, working_dir)` returns exactly
   `("word-counts-match- drafts",)` as the regression guard.

Revision 4 (2026-06-26, round-4 design review). Resolved both blocking points
and the three advisories:

1. **RECOUNT leaves `[gates]` stale (blocking point B1).** Verified against
   source that the §5.2 `gate-ratio-consistent` validator checks gates against
   the **table** total `sum(by_chapter.values())` (`validate.py:247-275`, line
   260) while the corpus derives honest gates from the **draft** total
   `sum(chapter.draft_words)` (`_variants.py:36-40`) — so the headline
   variant's two totals differ by construction. Re-deriving gates from the
   ratio (Wafflecat alternative (a)) is **rejected** because a gate flag
   records "threshold crossed **and** the pass integrated and logged"
   (`state-layout.md:104,174-177`; design §5.2 line 469-470), an agent
   judgement disk does not store; fabricating it violates "disk authoritative,
   never the reverse". Adopted review option (b), made airtight by Decision Log
   **D-GATES** and a new Constraint: word-count reconciliation is in scope
   **only for sub-threshold divergences**, both word-count variants are built
   sub-threshold, and Work item 4 adds a **post-repair gate-clean test**
   (`validate_state` returns no `gate-ratio-consistent` violation after
   `RECOUNT`) plus a stated, tested scope boundary (a threshold-crossing
   divergence is a Tolerance breach — "Gate-crossing divergence" — that
   `reconcile` reports and escalates, never mis-repairs). The `recount`
   command's own `_refuse_if_incoherent` (`_recount.py:148`) is the
   belt-and-braces backstop. Closes the Doggylump pre-mortem (the recovery
   routine looping on its own repair). Corrected: Status summary, Controlling
   decision (item 1), Constraints, Tolerances, Risks, D-GATES, Work item 4,
   Acceptance.
2. **Recount-only narrows §5.4's named reconstruction (blocking point B2).**
   (i) Recorded that the recount-only reading is a **design-level** narrowing
   of §5.4 lines 489-492 (changing what the reconciliation *reads*), so per
   AGENTS.md "Project documentation" (181-183) Work item 6 now writes a §5.4
   design-doc note (and an ADR if substantive) as a **gating** deliverable —
   elevated from the round-3 "only if a design-level decision needs recording"
   wording (Decision Log **D-DESIGN-NOTE**). (ii) Named and tested the genuine
   §5.4 worked case — a real `done.flag` over a **non-empty** draft the table
   **under-counts**, which does **not** trip `done-flag-without-draft`
   (`_oracle.py:206-215` keys on `draft_words == 0`) and lands as
   `word-counts-match-drafts` → `RECOUNT`: added the corpus variant
   `done-flag-real-draft-undercount` (Work item 1), its sole-violation and
   twin-equality coverage, and an end-to-end behavioural test plus the
   post-repair gate-clean assertion (Work item 4). Corrected: Status summary,
   Controlling decision (the §5.4 worked-example paragraph), D-DESIGN-NOTE,
   Work items 1/4/6, Acceptance.
3. **Advisories.** A1: documented that the `manifest-disk-bijection` corpus twin
   reads the **spec** (`_oracle.py:152-165`, `_SPEC_CHECKS`), not disk, so the
   implementer pins the right oracle and does not "fix" it (Work item 1). A2:
   the `cursor-plan-present` → `REFUSE` mapping is a §5.2-invariant-6
   interpretation and is recorded in the §5.4 design-doc note (D-REPORT,
   D-DESIGN-NOTE). A3: the stale Risk "reconcile brackets with the
   `pending_turn` context manager" is rewritten to the manual bracket of
   D-SELF, so the living document is internally consistent.

No remaining undecided forks: the gate-staleness mechanism is pinned (a
sub-threshold construction plus a post-repair gate-clean test, with gates never
fabricated), the §5.4 narrowing has a gating design-doc deliverable, and the
design's worked example is tested.

## Addenda (post-merge follow-ups)

Lightweight addendum work items surfaced by a test-quality benchmark of the
reconcile behavioural suite. Execute each as a small addendum pass — no plan or
design-review cycle: make the change, run `make all`, `coderabbit review
--agent`, commit, and tick the matching roadmap sub-task on merge.

- [ ] 2.3.2.1 — Strengthen the reconcile log-receipt assertion from the
  substring `"recount" in log` to a structured receipt that pins the operation
  and the repaired field set (the design's audited reconciliation entry).
  Behaviour-preserving test change; gate with `make all`.
- [ ] 2.3.2.2 — Add an assertion that every chapter `draft.md` is byte-for-byte
  identical before and after `reconcile` (today only "no file removed" is
  pinned, not draft byte-integrity; only `state.toml`/`log.md` should change).
  Test-only change; gate with `make all`.
