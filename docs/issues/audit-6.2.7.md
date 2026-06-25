# Post-merge audit: roadmap task 6.2.7

Audit of the codebase after roadmap task 6.2.7 ("add a reconcile-boundary
`ROLLBACK_PENDING_TURN` recovery scenario", commit `10ff403`) merged to `main`.
The task closed the symmetric half of the torn-multi-file-turn recovery story:
task 6.2.5 proved the `COMPLETE` disposition at the `novel-state` command
boundary from a real torn turn; the `ROLLBACK` disposition had only the pure
`derive_reconciliation` classifier test and an in-process body-call test over a
hand-planted corpus fixture. Task 6.2.7 added a behavioural (pytest-bdd)
scenario that produces a genuine torn turn through the design §3.4 `pending_turn`
producer bracket (raising mid-turn over `wc.COHERENT_BASELINE` declaring an
unrecoverable `working/manuscript/chapter-99/draft.md` that never lands), then
drives recovery through the shared command runner: `check` reports the torn turn
at exit 4 with a `rollback-pending-turn` reconciliation, and a single `reconcile`
rolls it back at exit 0. The commit message records, accurately, that no
production code changed.

The new work is correct, faithfully documented, paired with semantic assertions
(no behaviour is snapshot-only, per AGENTS.md), and en-GB Oxford-spelling clean.
The feature narrative, the step docstrings, and the binder docstring all check
out against the design (§3.4 the `pending_turn` bracket, §5.4 item 2 "Rolling
back removes nothing") and against the sibling 6.2.5 recovery suite they mirror.
The findings below are all low-to-medium hygiene observations; the headline one
is that this test-only task added a **fourth** verbatim copy of the
reconcile-family command-driving scaffolding that roadmap task 7.23.3 already
tracks — but whose named scope predates this copy. None block the merge.

Sources relied on: `docs/issues/audit-6.2.5.md` (the COMPLETE-disposition sibling
this task mirrors) and `docs/issues/audit-6.2.8.md` (the most recent audit, for
format and the carried duplication themes); `docs/roadmap.md` (tasks 6.2.7,
7.14.1, 7.23.3, 7.23.4); `docs/developers-guide.md` ("Shared test scaffolding",
which forbids "a fresh copy in each module"); `docs/novel-ralph-harness-design.md`
(§3.4 the `pending_turn` bracket and torn-turn recovery, §5.4 item 2 the
rollback-removes-nothing rule); and `AGENTS.md` (snapshot-pairing, the 400-line
module cap, en-GB Oxford spelling). Code navigated with `leta`; the 6.2.7 change
set traced with `git show` over commit `10ff403`. Skills consulted:
`python-router`, which routed to `python-testing` (pytest-bdd step and fixture
discipline) for the test-scaffolding findings.

## Finding 1: Task 6.2.7 added a fourth copy of the reconcile-family driver scaffolding

- **Category:** duplication
- **Severity:** medium
- **Location:** `tests/steps/torn_turn_rollback_steps.py:89-132` (the verbatim
  `_draft_bytes`, `_present_files`, `_run`, and `_run_capturing` helpers, plus the
  `_COMMAND` constant and the `_Outcome` dataclass skeleton), duplicating
  `tests/steps/torn_turn_recovery_steps.py:89-132` line-for-line.

The four command-driving helpers in the new ROLLBACK step module are byte-for-byte
identical to those in `torn_turn_recovery_steps.py` (the 6.2.5 COMPLETE sibling):
`_draft_bytes` and `_present_files` differ only in a docstring word ("recovery"
versus "rollback"), and `_run`/`_run_capturing` are exact copies. The `run_check`
and `follow_up_check_clean` step bodies, and the `_present_files <= after` plus
`drafts_after == drafts_before` integrity assertion, are also reproduced. The new
module's own docstring (lines 33-35) cites "ExecPlan Decision D-DUP" to justify
keeping the helpers self-contained "rather than shared", but the developers' guide
is explicit that "New shared scaffolding belongs in `tests/conftest.py` as another
fixture rather than a fresh copy in each module"
(`docs/developers-guide.md:54-56`). This is the precise duplication roadmap task
7.23.3 already tracks — but 7.23.3 names only three sites
(`torn_turn_recovery_steps.py`, `reconcile_steps.py`, and
`test_reconcile_integration.py`); the new `torn_turn_rollback_steps.py` is a
fourth copy its Requires/Success scope does not yet name. So the tracked
consolidation has silently grown by one module without the roadmap reflecting it.

- **Proposed fix:** No new consolidation work — task 7.23.3 owns the
  `drive()` / `crash_after_recovery_receipt()` / `draft_bytes` / `present_files`
  registered-plugin home. Widen 7.23.3's scope to name
  `tests/steps/torn_turn_rollback_steps.py` as a fourth delegating site (it shares
  the `drive()`/`draft_bytes`/`present_files` helpers, though not the
  crash-injection seam — its producer is the §3.4 `pending_turn` bracket, not the
  `_append_recovery_entry` monkeypatch). Recording this in the audit so the root
  agent can extend 7.23.3 rather than letting the copy count drift unrecorded.

## Finding 2: The ROLLBACK scenario does not assert the partial torn artefacts are left in place

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/steps/torn_turn_rollback_steps.py:275-290`
  (`rollback_preserves_files`), and the scenario's choice of `_UNRECOVERABLE_DRAFT`
  at line 69.

Design §5.4 item 2 has two halves: a rollback "removes nothing" *and* leaves the
partial artefacts that did land in place (it clears only the `[pending_turn]`
record, fabricating no prose). The scenario picks an unrecoverable artefact —
`working/manuscript/chapter-99/draft.md` — that the coherent baseline never
materialises, so it never lands; `rollback_preserves_files` therefore proves only
the "removes nothing" half (`files_before <= after` and drafts unchanged). A torn
turn whose *recoverable* sibling artefacts (a `state.toml` edit, a partial
`log.md` line) did land before the unrecoverable one failed is not exercised, so
the "leaves the landed partial in place" half of §5.4 item 2 has no
command-boundary proof. The chosen scenario is the cleanest ROLLBACK trigger, but
it is also the one that exercises the least of the rollback contract's preserve
guarantee.

- **Proposed fix:** Either (a) add one assertion to `rollback_preserves_files`
  that the `after` file set still contains every recomputable artefact named
  in the declared `paths` that *did* land (vacuous now because none land, but it
  documents the intent and would catch a future variant), or (b) note in the step
  docstring that this scenario deliberately exercises only the "removes nothing"
  half because the declared artefact is the sole one in flight, deferring the
  landed-partial-preservation case to a corpus variant. Option (b) is the lighter
  touch and keeps the single-artefact scenario honest about its coverage.

## Finding 3: ROLLBACK at the command boundary is proven only for an unrecoverable draft.md, not a done.flag

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/steps/torn_turn_rollback_steps.py:65-69` (`_UNRECOVERABLE_DRAFT`
  is the sole unrecoverable trigger), against
  `novel_ralph_skill/state/reconcile.py:88-89` and `:177-216`.

`_classify_pending_turn` (and the module docstring at `reconcile.py:22-24`)
treats two basenames as unrecoverable triggers for `ROLLBACK`: a `draft.md` body
**and** a `done.flag`. The new command-boundary scenario exercises only the
`draft.md` trigger. The `done.flag` trigger remains covered only by the pure
classifier test
(the in-process layer 6.2.7's commit message says it supersedes for `draft.md`),
so the command-boundary half of the disposition is asymmetric: the
`draft.md`-unrecoverable path is now proven end-to-end through the runner, the
`done.flag`-unrecoverable path is not. This is a narrowing of the same kind 6.2.7
was created to close (an in-process-only proof for a disposition the command
boundary should demonstrate).

- **Proposed fix:** Record a low-severity follow-up (candidate roadmap item under
  step 6.2 or wherever the torn-turn surface coverage is tracked) to add a second
  parametrisation of the ROLLBACK scenario declaring an unrecoverable `done.flag`
  rather than a `draft.md`, so both branches of `_RECOMPUTABLE_BASENAMES`-exclusion
  have a command-boundary proof. The existing scenario already parametrises cleanly
  on `_UNRECOVERABLE_DRAFT`; a `pytest.mark.parametrize` over `(declared_path,
  expected_basename)` would cover both with one step module.

## Finding 4: The `_RECONCILE_PATHS` / declared-path basename rule is duplicated as a test literal

- **Category:** duplication
- **Severity:** low
- **Location:** `tests/steps/torn_turn_rollback_steps.py:65-69`
  (`_UNRECOVERABLE_DRAFT` plus its inline comment re-deriving the
  `{"state.toml", "log.md"}` recomputable rule) against the production source of
  truth `novel_ralph_skill/state/reconcile.py:89` (`_RECOMPUTABLE_BASENAMES`).

The step module's comment re-states the production classification rule ("its
basename is not in `{state.toml, log.md}` ... so the missing path is
unrecoverable → ROLLBACK") to justify the chosen literal. This is the same class
of re-literalised-corpus-knowledge that roadmap task 7.23.4 flags for the recount
target (`_RECOUNT_TARGET` in `torn_turn_recovery_steps.py`): the test encodes,
in prose and in a hand-picked path, a rule the production module already owns. If
`_RECOMPUTABLE_BASENAMES` ever gained a third recomputable basename, this
scenario's choice of trigger could silently stop being unrecoverable and the test
would pass green for the wrong reason.

- **Proposed fix:** No standalone work; fold into the 7.23.4 theme (let the
  corpus / production own the data the command-driving tests assert against). When
  7.23.4 lands, expose the `ROLLBACK`-triggering unrecoverable basenames (or a
  ready-made unrecoverable declared path) from `working_corpus` or alongside
  `_RECOMPUTABLE_BASENAMES`, and have the scenario import it rather than hand-pick
  `chapter-99/draft.md`, so the test cannot drift from the production rule.

## Finding 5: Pre-existing — the `[word_counts]` write and function-local import remain triplicated

(carried theme; not widened by 6.2.7, already tracked)

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_recount.py:146-147`,
  `novel_ralph_skill/commands/_reconcile.py:142-143` (`_recount_edit`), and
  `novel_ralph_skill/commands/_reconcile.py:176-177` (`_pending_turn_edit`), each
  open-coding `document["word_counts"]["current"] = ...; document["word_counts"]
  ["by_chapter"] = _inline_by_chapter(...)`; plus the function-local
  `from novel_ralph_skill.state import disk_word_counts` at `_reconcile.py:172`,
  which the module already imports at module level (`_reconcile.py:55-62` pulls
  many names from `novel_ralph_skill.state`, where `disk_word_counts` is
  exported).

Confirmed still present at this commit while reading the reconcile dispatch the
6.2.7 scenario drives. The three-site `[word_counts]` write plus its
validate-before-persist tail, the two near-identical `_recount_edit` /
`_pending_turn_edit` closures, and the avoidable function-local import are exactly
the cluster roadmap task 7.14.1 owns ("Consolidate the `[word_counts]` write
across recount and reconcile onto one shared validated writer"; the import lift
is named in its Success criteria). Recorded here only to confirm 6.2.7 did not
widen it — the task touched no production code — and that 7.14.1 is the right
home.

- **Proposed fix:** No new work — task 7.14.1 owns the
  `_write_word_counts_validated` consolidation and explicitly includes lifting the
  function-local `disk_word_counts` import in the same pass. No change needed from
  this task.
