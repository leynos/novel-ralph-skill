# Cover the partial-`init` bootstrap in disk-authoritative reconciliation

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: COMPLETE

## Purpose / big picture

`novel-state init` writes `working/state.toml` first and the empty
`working/log.md` second (`novel_ralph_skill/commands/novel_state.py::_init`,
lines 288 and 291), and refuses any re-run while `state.toml` exists (same
function, line 275; roadmap-2-2-2 Decision Log D3). A crash *between* those two
writes therefore leaves an otherwise-coherent tree with `state.toml` present and
`log.md` absent — a partial bootstrap that re-running `init` cannot repair
(it refuses) and that nothing else currently detects. `init` opens no
`[pending_turn]` bracket (roadmap-2-2-2 D3), so the torn-turn recovery path
(`novel_ralph_skill/state/reconcile.py`) never sees this case and it falls
through to `ReconcileAction.NONE` — silently unrecoverable.

After this change, a `working/` tree with `state.toml` present and `log.md`
absent is a *detected, repairable* condition. `novel-state check` reports it
(exit 4) with a `reconciliation` payload, and `novel-state reconcile` self-heals
it by recreating an empty `log.md`, appending a recovery receipt, and exiting 0,
deleting no file under `working/`. An operator can observe this end-to-end:

```console
$ rm working/log.md            # simulate the crash between init's two writes
$ novel-state check; echo $?
... "violations": ["log-present"] ...
4
$ novel-state reconcile; echo $?
... "action": "recreate-log" ...
0
$ test -f working/log.md && novel-state check; echo $?
0
```

This serves the step-2.3 hypothesis — state re-derivable from disk so it can
never drift — by giving multi-file turn recovery (which owns torn turns) the
partial-`init` case too. `log.md` is a *recomputable* artefact: `init` creates
it empty and every later writer only appends receipts, so recreating an empty
`log.md` fabricates no agent judgement and keeps disk authoritative
(design §5.4). The reconcile machinery already classifies `log.md` as
recomputable (`reconcile.py` `_RECOMPUTABLE_BASENAMES`, line 74), so the self-heal
is the design-aligned outcome, not a new policy.

## Constraints

Hard invariants that must hold throughout implementation.

- **No deletion.** `reconcile` must delete no file under `working/`
  (design §5.4 line 510; developers-guide line 240). The repair only *creates*
  an absent `log.md`.
- **`check` is strictly read-only** (design §3.3, §5.4 line 502). The new
  detection must live in `check_disk_evidence` /`derive_reconciliation` and write
  nothing.
- **Disk is authoritative; never the reverse** (design §5.4). The repair may
  recreate only artefacts that are deterministically recomputable from disk
  without an agent judgement. An empty `log.md` qualifies; nothing else is
  synthesised.
- **Single sanctioned writers.** `state.toml` is written only through
  `write_document_atomically` (ADR-002; design §5.3). `log.md` is written by the
  existing append/create helpers in `_reconcile.py` and `novel_state.py`; the
  direct-edit guard does not apply to `log.md` (novel_state.py line 289-290).
- **Loud reconciliation.** Every repair is reported in `result` *and* appended to
  `log.md` as a receipt (design §5.4 lines 512-514).
- **Shared derivation.** `check` and `reconcile` must not disagree: both route
  through the one pure `derive_reconciliation(state, working_dir)`
  (`reconcile.py`; D-SHARED). No payload is handed from `check` to `reconcile`.
- **Deliberate-twin discipline.** The corpus oracle
  (`tests/working_corpus/_oracle.py`) and the production detector
  (`novel_ralph_skill/state/disk_evidence.py`) are independent twins that must
  not import each other and must agree on every corpus tree (developers-guide
  §"Invariant validation"). A new invariant name must be added to **both** and
  pinned equal.
- **Owned-name vocabulary equality.** `DISK_EVIDENCE_INVARIANT_NAMES` must stay
  equal to the corpus oracle's disk-evidence subset
  (`test_owned_disk_evidence_names_equal_corpus_subset`,
  `tests/test_disk_evidence.py` line 62). The pure-state vocabulary pin
  (`test_owned_names_equal_corpus_vocabulary`,
  `tests/test_validate_state_corpus.py` line 62) is *unaffected* here — it pins
  the eight pure-state names, none of which move.
- **Corpus exhaustiveness.** `test_every_invariant_name_is_exercised`
  (`tests/test_working_corpus.py` line 471) asserts
  `{incoherent_tree(name)[2] for name in incoherent_variant_names} ==
  set(corpus_invariant_names)`: every name added to `CORPUS_INVARIANT_NAMES` must
  be the *target* of at least one materialisable incoherent variant. Adding
  `log-present` to the oracle vocabulary therefore *requires* a registered
  partial-init variant whose built tree has `log.md` absent (see Work item 2,
  the post-build mutation mechanism). A documented carve-out is the escalation
  fallback only (Tolerances), not the default.
- **No new external dependency, no new cuprum API.** The e2e proof reuses the
  locked `_build_and_install_novel_state` helper verbatim
  (`tests/test_novel_state_check.py` line 304; cuprum 0.1.0 pinned by `uv.lock`).
- **Files stay under 400 lines** (AGENTS.md hard cap, line 24). Three touched
  files are at or near the cap and **must all be watched**:
  `tests/working_corpus/_oracle.py` is **399** lines, `novel_state.py` is 375
  lines, and `disk_evidence.py` is 346 lines. `_oracle.py` is the binding one:
  Work item 2 adds the `LOG_PRESENT` constant, a `CORPUS_INVARIANT_NAMES` entry,
  the `_check_log_present` predicate (a docstring-bearing function, ~6 lines in
  house style), and the `passed[LOG_PRESENT] = ...` wiring line in `corpus_check`
  — roughly +9 lines, which crosses 400. This is anticipated, not a surprise:
  Work item 2a (below) extracts the **physically-disk-reading** predicate block
  out of `_oracle.py` into a sibling module **first**, dropping `_oracle.py` to
  roughly 260 lines, and the new twin is then added in the sibling. No
  mid-work-item improvisation is permitted (see Tolerances).
- **"Disk-reading" vs "disk-evidence" are two different sets — do not conflate
  them.** This plan distinguishes (a) the *physically-disk-reading* oracle
  predicates — the six predicates that take a `working_dir` parameter and read
  the materialised tree, wired into `corpus_check` at
  `tests/working_corpus/_oracle.py` lines 393-398:
  `_check_by_chapter_sum` (line 111, reads `state.toml`),
  `_check_manifest_disk_bijection` (line 170),
  `_check_done_flag_without_draft` (line 223),
  `_check_compiled_matches_drafts` (line 282),
  `_check_word_counts_match_drafts` (line 309), and
  `_check_cursor_plan_present` (line 329, takes `(spec, working_dir)`); from (b)
  the production-owned `DISK_EVIDENCE_INVARIANT_NAMES`
  (`disk_evidence.py` lines 71-78): `manifest-disk-bijection`,
  `cursor-plan-present`, `done-flag-without-draft`, `compiled-matches-drafts`,
  `pending-turn-cleared`, `word-counts-match-drafts`. The two sets are **not**
  the same: `by-chapter-sum` is physically-disk-reading in the oracle but is a
  *pure-state* name owned by `validate_state` (not in
  `DISK_EVIDENCE_INVARIANT_NAMES`); and `pending-turn-cleared` is in the
  production disk-evidence set but its oracle twin
  `_check_pending_turn_cleared` (line 244) reads the **spec**
  (`return spec.pending_turn is None`) and is a member of `_SPEC_CHECKS`
  (line 368), so it is a pure-spec twin that **must stay in `_oracle.py`**. Work
  item 2a moves set (a), the physically-disk-reading predicates, because file
  size is determined by what code physically lives in `_oracle.py`; the
  owned-name vocabulary in (b) is untouched by the move. No mid-work-item
  improvisation is permitted (see Tolerances).
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, comments,
  commits (AGENTS.md; en-gb-oxendict skill).

## Tolerances (exception triggers)

- Scope: if implementation needs changes to more than 10 source/test files or more
  than ~250 **net** lines, stop and escalate. The budget is 10 (not 8) because Work
  item 2a adds one new file (`tests/working_corpus/_oracle_disk.py`) and edits
  `_oracle.py`; the move itself is net-neutral (~145 lines of predicate bodies
  relocated, not added), so the net-line budget is unaffected by the extraction.
- Interface: if `derive_reconciliation`, `Reconciliation`, or `ReconcileAction`
  need a signature change beyond adding one enum member and reusing existing
  fields, stop and escalate.
- Dependencies: any new external dependency → stop and escalate.
- File size: `_oracle.py` (399) crossing 400 is **already resolved** by the
  pre-planned Work item 2a extraction — proceed with that extraction, do not
  escalate. Escalate only if (a) after the Work item 2a extraction `_oracle.py`
  is still ≥ 396 lines (the extraction failed to buy ~ headroom for Work item 2's
  additions), or (b) the `log-present` predicate would push `disk_evidence.py` or
  the new `_oracle_disk.py` sibling past 400. Never improvise an unplanned module
  split mid-work-item; the only sanctioned extraction is the Work item 2a one
  specified below.
- Design conflict: if self-heal cannot be expressed without violating the
  "no deletion" or "disk authoritative" constraint, stop and escalate; the
  documented-operator-routine fallback (roadmap 2.3.4 "or") is the escalation
  decision, not a silent substitution.
- Iterations: if `make all` still fails after 3 attempts on any work item, stop
  and escalate.

## Risks

- Risk: a new disk-evidence invariant double-fires with an existing one (for
  example, a tree missing both log.md and a draft). Severity: medium. Likelihood:
  medium. Mitigation: scope the `log-present` predicate narrowly — it fires only
  on `state.toml` present and `log.md` absent, independent of chapter/draft
  state — and give it non-refuse, lowest precedence so a genuine contradiction
  (REFUSE class) or a pending-turn still dominates in `derive_reconciliation`.
  Add a property/parametrised test asserting it never co-fires with a REFUSE
  member on the same tree.
- Risk: the corpus builder always materialises `log.md`
  (`tests/working_corpus/_builder.py` line 201), so a partial-init tree cannot be
  a pure spec variant, *and* `test_every_invariant_name_is_exercised`
  (`tests/test_working_corpus.py` line 471) forces every
  `CORPUS_INVARIANT_NAMES` member to be the target of a materialisable variant —
  so `log-present` cannot simply be added to the oracle vocabulary. Severity:
  high (a verbatim Work item 2 would fail `make all` with
  `missing: {'log-present'}`). Likelihood: high (confirmed by reading the test
  and the builder). Mitigation: Work item 2 introduces a **post-build mutation
  registry** — a `_POST_BUILD_MUTATIONS: dict[str, Callable[[Path], None]]` in
  `tests/working_corpus/_variants.py` keyed by variant name and applied inside
  the `incoherent_tree` fixture (`tests/corpus_fixtures.py` line 299) *after*
  `build_working_tree`. Register a coherent baseline spec under a new
  `INCOHERENT_VARIANTS["partial-init"]` entry whose oracle name is `log-present`,
  plus a `_POST_BUILD_MUTATIONS["partial-init"]` that unlinks `working/log.md`.
  This keeps the `INCOHERENT_VARIANTS` value shape `(spec, name)` intact for the
  fifteen-odd existing subscript consumers (`tests/test_reconcile*.py`,
  `tests/steps/*`), so no other consumer is disturbed; the mutation is applied
  only on the `incoherent_tree` path. The exhaustiveness assertion stays a true
  `==` (no carve-out), keeping the corpus a faithful exerciser of every oracle
  name.
- Risk: the existing twin-agreement safety net
  (`tests/test_novel_state_check_disk.py` line 132) iterates the same
  spec-built corpus, where `build_working_tree` always writes `log.md`, so it
  never sees a log-absent tree and therefore **never exercises `log-present`**.
  Severity: medium. Likelihood: high (structural). Mitigation: Work item 4 adds
  a dedicated agreement assertion that runs the production
  `check_disk_evidence` and the oracle `corpus_check` against the
  partial-init (log-absent) tree built via `incoherent_tree("partial-init")` and
  asserts both fire `log-present` and agree — restoring the twin-agreement
  guarantee for the one invariant the spec-built corpus cannot reach.
- Risk: `reconcile`'s manual D-SELF bracket declares paths
  `("state.toml", "log.md")` and recreates log.md as the receipt step — a
  recreate-log action could collide with that bracket's own log handling.
  Severity: medium. Likelihood: low. Mitigation: the recreate-log repair writes
  no `state.toml` change; it only needs the `log.md` receipt to exist. Reuse
  `_append_recovery_entry` (which opens log.md in append mode and creates it when
  absent) so the recreate and the receipt are the same write. Verify append-mode
  create behaviour with a unit test; do not route a no-op state write through the
  bracket.
- Risk: `tests/working_corpus/_oracle.py` is 399 lines (`wc -l` confirmed), one
  below the 400-line hard cap (AGENTS.md line 24), and Work item 2 must add ~9
  lines to it (the `LOG_PRESENT` constant, a `CORPUS_INVARIANT_NAMES` entry, the
  `_check_log_present` predicate with a house-style docstring, and the
  `passed[LOG_PRESENT] = ...` wiring), which crosses the cap. Severity: high (an
  implementer following Work item 2 verbatim hits the cap mid-work-item and is
  forced to escalate or improvise an unreviewed split). Likelihood: high
  (arithmetic certainty). Mitigation: Work item 2a (a dedicated, independently
  committable extraction sequenced **before** Work item 2) moves the **six
  physically-disk-reading** oracle predicates (those wired into `corpus_check` at
  lines 393-398): `_check_by_chapter_sum` (line 111),
  `_check_manifest_disk_bijection` (line 170), `_check_done_flag_without_draft`
  (line 223), `_check_compiled_matches_drafts` (line 282),
  `_check_word_counts_match_drafts` (line 309), and `_check_cursor_plan_present`
  (line 329), together with their private disk helpers
  (`_on_disk_chapter_numbers` line 155, `_disk_drafts` line 254,
  `_disk_present_draft_bodies` line 274, `_disk_by_chapter` line 297) into a new
  `tests/working_corpus/_oracle_disk.py` sibling, which `_oracle.py` imports.
  This is ~145 lines of predicate bodies out of `_oracle.py`, dropping it to
  roughly 260 lines and giving ample headroom; the new `log-present` twin
  (constant + predicate) is then added in the sibling in Work item 2, and only
  its name and the `passed[...]` wiring line touch `_oracle.py`. Both files stay
  well under 400. The pure-spec `_check_pending_turn_cleared` (line 244) does
  **not** move — it reads `spec.pending_turn` and belongs to `_SPEC_CHECKS`
  (line 368). The extraction is pure code-movement (no behaviour change), so the
  entire corpus/twin/agreement suite must stay green across the Work item 2a
  commit — that is its acceptance gate.
- Risk: the disk-evidence twin extraction (Work item 2a) silently changes a twin
  predicate's behaviour, breaking the production-vs-oracle agreement the corpus
  guarantees. Severity: high. Likelihood: low (movement only). Mitigation: move
  code verbatim (no edits to predicate bodies), re-export the moved names from
  `_oracle.py` so `corpus_check` and every existing importer keep their current
  symbols, and gate the commit on the full agreement suite
  (`tests/test_novel_state_check_disk.py`), the twin-equality pin
  (`tests/test_disk_evidence.py`), and the whole-corpus exhaustiveness tests
  (`tests/test_working_corpus.py`) all staying green with **no** vocabulary change
  (2a adds no invariant; it only relocates existing predicates).
- Risk: extending the §5.4 v1 reconcile scope (currently two corrections) without
  updating the design and developers-guide leaves the source-of-truth docs
  contradicting the code. Severity: medium. Likelihood: medium. Mitigation: Work
  item 5 updates design §5.4 v1-scope, the developers-guide invariant table, and
  the users-guide recovery section in the same plan, each gated by
  `make markdownlint` and `make nixie`.

## Progress

- [x] Work item 1: red — failing unit tests for the `log-present` disk-evidence
  invariant and its `RECREATE_LOG` reconciliation. Done: two `test_disk_evidence`
  tests (the log-absent firing test marked `xfail(strict=True)` until Work
  item 2, the log-present silent test passing now) and two
  `test_reconcile_derivation`
  tests (`xfail(strict=True)` until `RECREATE_LOG` lands in Work item 3). `make
  all` green (3 xfailed). Removed three superseded planning-scratch review files
  (`roadmap-2-3-4-review-round3.md`, `roadmap-2-3-4.review-r1.md`,
  `roadmap-2-3-4.review-r4.md`) that were breaking `make markdownlint`.
- [x] Work item 2a: refactor (behaviour-preserving) — extracted the six
  physically-disk-reading predicates (those taking `working_dir`, wired into
  `corpus_check`) and their disk helpers out of `tests/working_corpus/_oracle.py`
  (was 399 lines) into a new `tests/working_corpus/_oracle_disk.py` sibling,
  imported back so every importer is unchanged. The pure-spec
  `_check_pending_turn_cleared` stayed in `_SPEC_CHECKS`. After the move
  `_oracle.py` is 244 lines and `_oracle_disk.py` 199 lines (both well under the
  400-line cap). `make all` green, no vocabulary change (still 3 xfailed).
  Decision: kept the moved predicate docstrings verbatim (a coderabbit major
  finding suggested shortening them). The ExecPlan mandates a verbatim,
  behaviour-preserving move, and the docstrings carry the deliberate-twin
  documentation AGENTS.md requires ("comment why"); shortening would deviate from
  the plan and lose that. Two coderabbit minor findings targeted a planning-scratch
  review file already removed in Work item 1 (stale; moot).
- [x] Work item 2: green — added the `log-present` predicate to
  `disk_evidence.py` (`_check_log_present`, appended to `_PREDICATES` and
  `DISK_EVIDENCE_INVARIANT_NAMES`, exported as `LOG_PRESENT` from
  `state/__init__.py`) and its twin to `tests/working_corpus/_oracle_disk.py`; added
  the `LOG_PRESENT` name and `passed[...]` wiring to `_oracle.py`; added the
  `_POST_BUILD_MUTATIONS` registry, the `_remove_log_md` mutation, and the
  `partial-init` variant to `_variants.py`, exported `POST_BUILD_MUTATIONS` via
  the package, and wired the mutation into the `incoherent_tree` fixture. `make
  all` green (591 passed, 2 xfailed). Surprise: adding the registry pushed
  `_variants.py` to 405 lines, over the 400-line cap (pylint `too-many-lines`).
  The plan anticipated additions to `_variants.py` but did not flag the crossing.
  Resolved within Tolerances *without* an unplanned module split by condensing the
  `partial-init` inline comment and the registry/`_remove_log_md` prose to their
  essential "why" (no information lost); `_variants.py` is now 399 lines.
  coderabbit: one stale minor finding on an already-deleted scratch file.
- [x] Work item 3: extended `derive_reconciliation` with the `RECREATE_LOG`
  action (after `RECOUNT`, before `NONE`; `log-present` is *not* refuse-class) and
  wired the `reconcile` dispatch to recreate the absent `log.md` via
  `_append_recovery_entry` (the append-mode open is the create), writing no
  `state.toml` change and using no D-SELF bracket. Updated both module docstrings'
  precedence/dispatch lists. Removed the Work item 1 xfail markers (the two
  derivation tests now pass) and added `test_recreate_log_repairs_partial_init_tree`
  and `test_recreate_log_is_idempotent` to `test_reconcile.py`. `make all` green
  (595 passed, no xfails). coderabbit: three stale minor findings, all on
  already-deleted scratch review files (moot).
- [x] Work item 4: behavioural (`pytest-bdd`) + e2e coverage of the partial-init
  check/reconcile round-trip, plus a targeted `log-present` twin-agreement
  assertion over the log-absent tree. Done: added the `partial-init` case to the
  parametrised `test_disk_evidence_tree_exits_four_with_reconciliation` (check
  exit 4, `log-present`, `recreate-log` payload);
  `test_log_present_twin_agreement_over_partial_init_tree` (production vs oracle
  agreement on the log-absent tree the spec-built loop cannot reach); a new
  `reconcile.feature` partial-init scenario plus its steps; an entry-point and a
  slow installed e2e in `test_reconcile_e2e.py`; and a parametrised precedence
  property (`test_log_present_never_overrides_higher_precedence`) asserting
  `log-present` never overrides a higher-precedence action — the finite corpus is
  the right adversary (`python-verification`), so no Hypothesis run was needed.
  `make all` green (612 passed). coderabbit: zero findings.
- [x] Work item 5: documentation — design §5.4 scope, developers-guide,
  users-guide recovery routine; snapshot refresh. Done in lockstep: design §5.4
  v1-scope lead-in "two"→"three" and a new numbered item 3 for the recreate-log
  repair (verified with the `grep -Pzo` count checks: "three" matches, "two"
  does not, and the "deferred" prose does not name the repair); the
  developers-guide disk-evidence paragraph "Six"→"Seven" in both count
  statements, `log-present` added to the enumeration, and the mis-named pin
  reference corrected to `test_owned_disk_evidence_names_equal_corpus_subset` (the
  "eight owned names"/"seven §5.2 invariants" pure-state figures untouched); a
  users-guide recovery bullet for the partial-`init` recreate-log repair. No
  snapshot refresh needed: the new `recreate-log` action appears in no captured
  envelope (the partial-init check/reconcile tests assert semantically), and `make
  all` showed no snapshot mismatch. `make all`, `make markdownlint`, and `make
  nixie` all green.

## Surprises & discoveries

- Observation: roadmap-2-2-2 D3 prose says the realisable partial-init is "log
  present, state absent", but `_init` writes state.toml first then log.md, so the
  realisable case is the inverse — state present, log absent — exactly what
  roadmap 2.3.4 targets. Evidence:
  `novel_ralph_skill/commands/novel_state.py` lines 288 and 291; roadmap.md lines
  700-704. Impact: confirms the detection condition is "state.toml present and
  log.md absent"; note the D3 prose discrepancy in the implementation's Decision
  Log but do not edit roadmap-2-2-2 (off this task's scope).

## Decision log

- Decision: Self-heal the missing `log.md` rather than document an operator
  routine. Rationale: roadmap 2.3.4 offers "either self-heal ... or document the
  operator's init-rerun routine". `log.md` is recomputable (empty at init,
  append-only after; `reconcile.py` already lists it in `_RECOMPUTABLE_BASENAMES`),
  so recreating an empty receipt fabricates no agent judgement and satisfies §5.4
  "disk authoritative, no deletion". The operator-routine fallback is weaker
  (leaves the tree unrecoverable by command) and is reserved as the escalation
  outcome only if a constraint blocks self-heal. Date/Author: 2026-06-24, planning
  agent.
- Decision: Add a new owned disk-evidence invariant `log-present` (non-refuse,
  lowest precedence) and a new `ReconcileAction.RECREATE_LOG`, rather than
  overloading the pending-turn path. Rationale: `init` opens no `[pending_turn]`,
  so the pending-turn machinery does not apply; a dedicated, narrowly-scoped
  invariant keeps detection orthogonal and the precedence total (refuse →
  pending-turn → recount → recreate-log → none). Reusing fields on
  `Reconciliation` avoids a schema change. Date/Author: 2026-06-24, planning agent.
- Decision: Resolve the corpus-exhaustiveness collision with a **post-build
  mutation registry**, not a carve-out. Rationale:
  `test_every_invariant_name_is_exercised` (`tests/test_working_corpus.py` line
  471) requires every `CORPUS_INVARIANT_NAMES` member to be the target of a
  materialisable variant; `log-present` cannot be a pure spec variant because
  `build_working_tree` always writes `log.md` (`_builder.py` line 201) and the
  `INCOHERENT_VARIANTS` map is a pure `spec -> (spec, name)` map with no
  post-build hook. Option (a) — add a small `_POST_BUILD_MUTATIONS` registry
  applied in the `incoherent_tree` fixture and register a `partial-init` variant
  whose mutation unlinks `working/log.md` — keeps the exhaustiveness assertion a
  true `==` and the corpus a faithful exerciser of every oracle name. Option (b)
  — exempt `log-present` from the assertion — weakens the corpus's completeness
  guarantee and is reserved as the escalation fallback only. The registry is
  additive: it leaves the `INCOHERENT_VARIANTS` `(spec, name)` tuple shape intact
  for the ~15 existing subscript consumers, so no other test is disturbed.
  Date/Author: 2026-06-24, planning agent.
- Decision: Pre-authorise extracting the disk-evidence twin block from
  `tests/working_corpus/_oracle.py` into a new `tests/working_corpus/_oracle_disk.py`
  sibling as a dedicated, behaviour-preserving Work item 2a, sequenced before the
  `log-present` predicate is added. Rationale: `_oracle.py` is 399 lines (`wc -l`),
  one under the AGENTS.md 400-line hard cap (line 24); Work item 2 must add ~9
  lines (the `LOG_PRESENT` constant, a `CORPUS_INVARIANT_NAMES` entry, the
  `_check_log_present` predicate with its house-style docstring, and the
  `passed[LOG_PRESENT] = ...` wiring), which crosses the cap. A terse docstring
  alone cannot avoid this (399 + the minimum constant/entry/predicate/wiring is
  already ≥ 408). Reviewer offered (a) keep the addition under cap or (b) note the
  crossing and pre-authorise the extraction; (a) is arithmetically impossible, so
  (b) is taken. Moving the ~145-line physically-disk-reading block (the six
  predicates that take `working_dir` and are wired into `corpus_check` at lines
  393-398 — `_check_by_chapter_sum`, `_check_manifest_disk_bijection`,
  `_check_done_flag_without_draft`, `_check_compiled_matches_drafts`,
  `_check_word_counts_match_drafts`, `_check_cursor_plan_present` — plus their
  `_disk_*`/`_on_disk_chapter_numbers` helpers) into a sibling drops `_oracle.py`
  to roughly 260 lines and is pure code-movement, so the entire
  corpus/twin/agreement suite is the green gate for the 2a commit. The pure-spec
  `_check_pending_turn_cleared` (`return spec.pending_turn is None`, a member of
  `_SPEC_CHECKS`) does **not** move. The new `log-present` twin then lands in the
  sibling, so only its name and one wiring line re-enter `_oracle.py`. This
  removes the only path to a surprise mid-Work-item-2 escalation. Date/Author:
  2026-06-24, planning agent.
- Decision: Restore twin-agreement coverage for `log-present` explicitly.
  Rationale: the existing agreement suite
  (`tests/test_novel_state_check_disk.py` line 132) iterates the spec-built
  corpus, where `log.md` is always present, so it never reaches the new
  invariant. Work item 4 adds a targeted agreement assertion over the
  `incoherent_tree("partial-init")` (log-absent) tree so production
  `check_disk_evidence` and oracle `corpus_check` are still pinned equal on the
  one tree the spec-built corpus cannot express. Date/Author: 2026-06-24,
  planning agent.
- Decision: The e2e proof reuses the locked `_build_and_install_novel_state`
  cuprum helper verbatim; no new cuprum API is introduced. Rationale: cuprum 0.1.0
  (uv.lock) is verified to support catalogue construction
  (`ProgramCatalogue(projects=...)`,
  `ProjectSettings(name, programs, documentation_locations, noise_rules)`),
  absolute-path `Program` allowlisting (the catalogue allowlist is the gate,
  `cuprum/catalogue.py`), and `sh.make(prog, catalogue=...)(...).run_sync(
  context=ExecutionContext(cwd=...), capture=True)` returning
  `.exit_code/.stdout/.stderr` (`cuprum/sh.py`). The partial-init e2e needs no
  capability beyond what the `check`/`reconcile` e2e already exercise, so no
  firecrawl research into new library behaviour is required. Date/Author:
  2026-06-24, planning agent.

## Outcomes & retrospective

All five work items landed as five atomic commits, each gated green by `make all`
(plus `make markdownlint`/`make nixie` where markdown changed) before commit. The
partial-`init` bootstrap is now a detected, repairable condition: `check` reports
`log-present` at exit 4 with a `reconciliation` payload, and `reconcile`
recreates an empty `log.md`, appends a `recreate-log` receipt, exits 0, and
deletes nothing — proven by unit, derivation, twin-agreement, behavioural, e2e,
and precedence tests. Final `make all`: green.

Deviations and lessons:

- Work item 2's `_POST_BUILD_MUTATIONS` registry pushed `tests/working_corpus/
  _variants.py` to 405 lines, over the 400-line cap — a gap the plan did not
  flag. Resolved within Tolerances by condensing duplicated comment prose (no
  information lost, no unplanned module split), landing at 399 lines.
- `make fmt` runs `mdformat-all`, which reflows nearly every markdown file in the
  tree (the long-standing spurious-churn issue prior tasks all stashed). The
  churn was parked in `git stash` so only the intended doc edits were committed;
  `make all` runs `check-fmt`, which does not mutate, so the gate stayed clean.
- coderabbit findings across the run were either zero or stale references to the
  planning-scratch review files removed in Work item 1; no actionable code
  finding surfaced.

### Fix round 1 (2026-06-24)

Resolved two blocking dual-review findings. Both stemmed from Work item 5
having reached past its authorised additive edit (developers-guide lines
336-348) and disturbed adjacent source-of-truth prose, breaching the
Risks line 252-257 constraint that the docs must not contradict the code.

1. **Restored the deleted disk-vs-disk twin paragraph (developers-guide).**
   Work item 5 had deleted the entire disk-evidence twin-discipline paragraph
   (origin/main lines 437-453) — the disk-vs-disk twin prose, the
   both-sides-glob independence rule, and the two pins
   `test_union_detector_agrees_with_corpus_oracle` and
   `test_word_counts_twin_equals_corpus_oracle` (both tests still present in
   `tests/test_novel_state_check_disk.py` and `tests/test_disk_evidence.py`).
   That paragraph is the deliverable of roadmap item 2.3.3.2, still OPEN at
   roadmap.md:688, so its removal was out of scope for 2.3.4 and was recorded
   in no Progress/Decision-Log/Outcomes entry. Restored it and updated it in
   place for 2.3.4: six -> seven disk-evidence invariants, `log-present` added
   to the enumeration, and the both-sides-glob claim qualified so it stays
   accurate (the six manuscript-comparing twins glob `manuscript/chapter-*`;
   the `log-present` twin reads `log.md`'s presence on disk on both sides — the
   cross-check is disk-vs-disk in every case).
2. **Fixed the self-contradicting `disk_evidence.py` module docstring.** The
   task changed the opening "six" -> "seven" (correct) but left two downstream
   passages stale — a contradiction absent on origin/main. Line 33 "All six
   twins now read disk on both sides" now reads "The six manuscript-comparing
   twins ... The seventh twin, `log-present` (task 2.3.4), likewise reads disk
   on both sides", and the owned-names comment's wrong "the sixth is new this
   task (D-WORDCOUNT)" now attributes the sixth (`word-counts-match-drafts`) to
   task 2.3.2 and names `log-present` as the seventh and the one new this task
   (2.3.4).

No code behaviour changed. `make all` (612 passed), `make markdownlint`, and
`make nixie` all green; coderabbit returned one stale finding on an
already-deleted scratch review file (moot, outside scope). Committed atomically
(c135fa4).

## Context and orientation

This repository is a Python skill package. The five `novel-state` subcommands are
Cyclopts apps wired through a shared envelope runner. The pieces this plan touches:

- `novel_ralph_skill/state/disk_evidence.py` — the §5.4 disk-evidence detector.
  `check_disk_evidence(state, working_dir) -> tuple[Violation, ...]` runs six
  per-invariant predicates (assembled in `_PREDICATES`, lines 312-319) and is
  the production twin of the corpus oracle. Owned names are module constants
  (lines 61-66) collected in `DISK_EVIDENCE_INVARIANT_NAMES` (lines 71-78).
- `novel_ralph_skill/state/reconcile.py` — the pure, total
  `derive_reconciliation(state, working_dir) -> Reconciliation` shared by `check`
  and `reconcile`. `ReconcileAction` (lines 77-84) is a `StrEnum`;
  `Reconciliation` (lines 87-120) is a frozen dataclass. Precedence is
  refuse-class → pending-turn → recount → none (lines 231-247).
- `novel_ralph_skill/commands/_reconcile.py` — the `reconcile` mutator body. It
  dispatches on `reconciliation.action` (lines 261-281). `_append_recovery_entry`
  (lines 74-84) opens `working/log.md` in append mode — which *creates* the file
  when absent — and writes one timestamped receipt line.
- `novel_ralph_skill/commands/novel_state.py` — hosts `_check` (lines 195-240),
  `_init` (lines 243-296), `_render_reconciliation` (lines ~155-173), and
  `_disk_evidence_or_state_error` (lines 176-192). `_check` unions the pure-state
  and disk-evidence verdicts and attaches a `reconciliation` payload when disk
  evidence fired (lines 229-232).
- `tests/working_corpus/_oracle.py` — the independent corpus oracle, **399 lines**
  (`wc -l`), one under the AGENTS.md 400-line hard cap. `CORPUS_INVARIANT_NAMES`
  (lines 66-81) and the per-invariant `_check_*` predicates; `corpus_check(spec,
  working_dir)` (line 372) assembles `passed` from `_SPEC_CHECKS` (the pure-spec
  twins, line 360-369) and the **six physically-disk-reading** checks wired at
  lines 393-398 (`passed[BY_CHAPTER_SUM] = _check_by_chapter_sum(working_dir)`
  through `passed[WORD_COUNTS_MATCH_DRAFTS] = ...`), returning the violated names
  in vocabulary order. The six physically-disk-reading predicates —
  `_check_by_chapter_sum` (line 111, reads `state.toml`),
  `_check_manifest_disk_bijection` (line 170), `_check_done_flag_without_draft`
  (line 223), `_check_compiled_matches_drafts` (line 282),
  `_check_word_counts_match_drafts` (line 309), and `_check_cursor_plan_present`
  (line 329, takes `(spec, working_dir)`) — and their `_disk_*` helpers
  (`_on_disk_chapter_numbers` line 155, `_disk_drafts` line 254,
  `_disk_present_draft_bodies` line 274, `_disk_by_chapter` line 297) form a
  ~145-line block that Work item 2a relocates into a sibling so the file regains
  headroom. The pure-spec `_check_pending_turn_cleared` (line 244,
  `return spec.pending_turn is None`) is in `_SPEC_CHECKS` (line 368) and
  **stays** in `_oracle.py`. The new `log-present` twin
  (`_check_log_present(working_dir)` testing `(working_dir / "log.md").exists()`,
  firing on a log-absent tree) is added in that sibling.
- `tests/working_corpus/_oracle_disk.py` — **new** in Work item 2a: the relocated
  six physically-disk-reading predicates (`_check_by_chapter_sum`,
  `_check_manifest_disk_bijection`, `_check_done_flag_without_draft`,
  `_check_compiled_matches_drafts`, `_check_word_counts_match_drafts`,
  `_check_cursor_plan_present`) and their `_disk_*`/`_on_disk_chapter_numbers`
  helpers, re-exported through `_oracle.py` so `corpus_check`,
  `tests/working_corpus/__init__.py`, and every existing importer keep their
  current symbols. The pure-spec `_check_pending_turn_cleared` is **not** here —
  it stays in `_oracle.py`'s `_SPEC_CHECKS`. The `log-present` twin lands here.
- `tests/working_corpus/_variants.py` — `INCOHERENT_VARIANTS:
  dict[str, tuple[WorkingTreeSpec, str]]` (line 222), a pure
  `spec -> (spec, oracle-name)` map with **no** post-build mutation hook. Its
  `(spec, name)` tuples are unpacked by subscript across ~15 sites
  (`tests/test_reconcile*.py`, `tests/steps/*`); the shape must stay intact.
- `tests/working_corpus/_builder.py` — `build_working_tree(spec, dest)`
  materialises a `working/` tree and **always** writes an empty `log.md`
  (line 201). A partial-init tree must therefore have its `log.md` removed by a
  test-only post-build mutation, not by a spec flag.
- `tests/corpus_fixtures.py` — the `incoherent_tree` fixture (line 275) calls
  `build_working_tree` inside its `_build` closure (line ~299) and returns
  `(spec, working_dir, expected_name)`. This is the single chokepoint where a
  post-build mutation registry is applied.
- `tests/test_working_corpus.py` — `test_every_invariant_name_is_exercised`
  (line 471) pins `{incoherent_tree(name)[2] for name in
  incoherent_variant_names} == set(corpus_invariant_names)`; and
  `test_each_variant_breaks_exactly_its_invariant` (line 444) requires each
  variant's built tree to break *exactly* its one named invariant.
- `tests/features/reconcile.feature` + `tests/steps/reconcile_steps.py` — the
  `pytest-bdd` behavioural suite for `reconcile`.
- Test entry points already present: `tests/test_disk_evidence.py` (twin
  equality), `tests/test_novel_state_check_disk.py` (agreement suite),
  `tests/test_reconcile*.py`, `tests/test_reconcile_e2e.py`.

Terms of art:

- **Disk-evidence invariant** — a rule deciding whether `state.toml` has drifted
  from the on-disk `working/` tree (as opposed to a pure-state invariant, which
  decides whether `state.toml` contradicts itself).
- **Recomputable artefact** — a declared file the harness can re-derive from disk
  without an agent judgement (`state.toml`, `log.md`); contrasted with
  unrecoverable artefacts (`draft.md`, `done.flag`).
- **Refuse-class** — disk-evidence violations the reconciler reports but never
  auto-repairs (contradictions and `cursor-plan-present`).

## Plan of work

Stage A is understanding (this document). Stages B-D are the work items below,
each independently committable and gate-passable.

### Work item 1 (Stage B, red): failing unit tests for `log-present`

Docs to read: design §3.4 (atomic writes, init's two writes), §5.4 (v1 reconcile
scope); `skill/novel-ralph/references/state-layout.md` §"Initialisation" (step 3
creates empty log.md) and §"log.md" (append-only receipt); roadmap.md task 2.3.4.
Skills: `python-router` → `python-testing`; `leta` for navigation.

Add failing tests, no production change yet:

- In `tests/test_disk_evidence.py`: a test materialising a coherent baseline tree,
  deleting `working/log.md`, and asserting `check_disk_evidence(state, working)`
  returns exactly one `Violation` whose `invariant == "log-present"`; and a test
  asserting a tree *with* `log.md` does not emit `log-present`.
- In a new `tests/test_reconcile_derivation.py` case (or extend the existing
  file): assert `derive_reconciliation` over the log-absent tree returns
  `ReconcileAction.RECREATE_LOG` with the `log-present` discrepancy, and that a
  log-absent tree that *also* trips a refuse-class violation still returns
  `REFUSE` (precedence). These reference the not-yet-existing
  `ReconcileAction.RECREATE_LOG`, so mark them `xfail(strict=True)` until
  Work item 3 lands, or split the import-dependent assertions behind a guard.

Tests: unit. Validation: `make test` shows the new tests collected and failing
(or xfail-strict), not erroring on import.

### Work item 2a (Stage C, behaviour-preserving refactor): extract the physically-disk-reading predicates to a sibling

This work item exists solely to create the file-size headroom Work item 2 needs:
`tests/working_corpus/_oracle.py` is **399** lines (`wc -l`), one under the
AGENTS.md 400-line hard cap (line 24), and Work item 2 must add ~9 lines to it.
It changes **no** behaviour and adds **no** invariant — it only relocates existing
predicates — so the entire corpus / twin / agreement suite is its acceptance gate.

Docs to read: developers-guide §"Invariant validation" (the deliberate-twin
policy and the §5.4 disk-evidence narrative); AGENTS.md "Keep file size manageable"
(line 24) and "Group by feature, not layer" (line 32). Skills: `python-router` →
`leta` (find every importer of the moved symbols before moving them);
`en-gb-oxendict` for the new module docstring.

- Create `tests/working_corpus/_oracle_disk.py` and **move verbatim** (no edits
  to any predicate body) the **six physically-disk-reading** predicates from
  `_oracle.py` — the predicates that take a `working_dir` parameter and are wired
  into `corpus_check` at lines 393-398:
  `_check_by_chapter_sum` (line 111, reads `state.toml` via `tomllib`),
  `_check_manifest_disk_bijection` (line 170),
  `_check_done_flag_without_draft` (line 223),
  `_check_compiled_matches_drafts` (line 282),
  `_check_word_counts_match_drafts` (line 309), and
  `_check_cursor_plan_present` (line 329, signature `(spec, working_dir)`) —
  together with their private disk helpers `_on_disk_chapter_numbers` (line 155),
  `_disk_drafts` (line 254), `_disk_present_draft_bodies` (line 274),
  `_disk_by_chapter` (line 297). Do **not** move `_check_pending_turn_cleared`
  (line 244): it reads the **spec** (`return spec.pending_turn is None`), is a
  member of `_SPEC_CHECKS` (line 368), and is the pure-spec twin of production
  `_check_pending_turn_cleared` (whose `_working_dir` argument is unused,
  `disk_evidence.py` line 193) — it must stay in `_oracle.py`. Carry over only
  the imports those moved functions use (`tomllib`, `Path`, the `_specs` helpers
  `concatenate_drafts` / `chapter_dir_name`, and — because `_check_cursor_plan_present`
  takes `spec` — the `WorkingTreeSpec` `TYPE_CHECKING` import). Give the new
  module a one-paragraph docstring stating it is the **physically-disk-reading**
  half of the corpus oracle, split out for file-size only, and that each moved
  predicate keeps the same role it had in `_oracle.py`: the five §5.4
  disk-evidence twins (`manifest-disk-bijection`, `done-flag-without-draft`,
  `compiled-matches-drafts`, `word-counts-match-drafts`, `cursor-plan-present`)
  remain twins of the same-named production predicates in
  `novel_ralph_skill/state/disk_evidence.py`, while `_check_by_chapter_sum`
  remains the on-disk reader of the *pure-state* `by-chapter-sum` name (owned by
  `validate_state`, not in `DISK_EVIDENCE_INVARIANT_NAMES`). Do **not** claim
  every moved predicate is a "disk-evidence twin": `_check_by_chapter_sum` is not
  (it twins a pure-state name), and the disk-evidence-owned `pending-turn-cleared`
  twin is the one predicate that did **not** move.
- In `_oracle.py`: `from ._oracle_disk import (...)` the moved predicates and any
  helper still referenced locally, and re-export the moved **names** through
  `_oracle.py`'s public surface (and `tests/working_corpus/__init__.py` if any are
  exported there) so `corpus_check` and every existing importer keep working with
  zero call-site edits. Use `leta refs` on each moved symbol first to enumerate
  importers and confirm none break.
- Do **not** move the pure-spec `_SPEC_CHECKS` predicates (including
  `_check_pending_turn_cleared`), `CORPUS_INVARIANT_NAMES`, the name constants,
  or `corpus_check` itself — they stay in `_oracle.py`, which keeps owning the
  vocabulary and the assembly. After the move `_oracle.py` is roughly 260 lines
  and `_oracle_disk.py` roughly 170 lines, both well under 400. (The ~145 lines
  of relocated predicate bodies leave `_oracle.py` at 399 − ~145 + a few import
  lines ≈ 260; the sibling carries the ~145 bodies plus its docstring and
  imports ≈ 170.)

Tests: no new tests — this is movement only. The existing suite is the gate:
`tests/test_working_corpus.py` (exhaustiveness and per-variant), the twin-equality
pin `tests/test_disk_evidence.py::test_owned_disk_evidence_names_equal_corpus_subset`
(line 62), and the agreement suite `tests/test_novel_state_check_disk.py`
(line 132) must all stay green with no vocabulary change. Validation: `make all`.
Confirm with
`wc -l tests/working_corpus/_oracle.py tests/working_corpus/_oracle_disk.py` that
both files are under 400. Commit before starting Work item 2.

### Work item 2 (Stage C): the `log-present` predicate, corpus twin, and partial-init variant

Docs to read: design §5.4; developers-guide §"Invariant validation" (deliberate
twin policy, owned-name table). Skills: `python-router` →
`python-errors-and-logging` (narrow predicate return), `python-data-shapes` (the
mutation-registry type), `leta`.

Production predicate (the §5.4 detector):

- In `novel_ralph_skill/state/disk_evidence.py`: add `LOG_PRESENT: typ.Final =
  "log-present"`, append it to `DISK_EVIDENCE_INVARIANT_NAMES` (last, lowest
  precedence), and add

  ```python
  def _check_log_present(_state: State, working_dir: Path) -> Violation | None:
      """Return a violation when ``state.toml`` is present but ``log.md`` is absent."""
  ```

  returning a `Violation(invariant=LOG_PRESENT, ...)` iff
  `working_dir / "log.md"` does not exist. The `state` parameter is unused (the
  caller already loaded `state`, proving `state.toml` present), so it **must** be
  named `_state` to satisfy Ruff ARG001 — matching the established convention
  (`_check_pending_turn_cleared(state, _working_dir)`, `disk_evidence.py`
  line 193). Append the predicate to `_PREDICATES`. Keep it small and total. Mind
  the 400-line ceiling (the file is 346 lines) — if the addition crosses it,
  extract the predicate into a small sibling module and import it (escalate per
  Tolerances first).

Corpus twin (the independent oracle):

- Add the twin `LOG_PRESENT = "log-present"` constant to `_oracle.py` (it owns the
  name vocabulary) and append it to `CORPUS_INVARIANT_NAMES` (last). Add the
  predicate `_check_log_present(working_dir: Path) -> bool` returning
  `(working_dir / "log.md").exists()` **in the new `tests/working_corpus/_oracle_disk.py`
  sibling** (Work item 2a), beside the other disk-reading twins, with a terse
  house-style docstring ("Return True when ``log.md`` is present (§5.4).
  Disk-reading twin of production ``_check_log_present``."). Import it into
  `_oracle.py` and wire it into `corpus_check`'s `passed` map (after the other
  disk-reading checks) as `passed[LOG_PRESENT] = _check_log_present(working_dir)`.
  Net effect on `_oracle.py`: one constant line, one `CORPUS_INVARIANT_NAMES`
  entry, one import addition, and one `passed[...]` line — about +4 lines onto the
  post-2a ~210, so it stays far under the 400-line cap; the predicate body itself
  lands in the sibling.

Corpus post-build mutation + partial-init variant (resolves the exhaustiveness
collision — see Constraints "Corpus exhaustiveness" and the Decision Log):

- In `tests/working_corpus/_variants.py`: add a registry
  `_POST_BUILD_MUTATIONS: dict[str, cabc.Callable[[Path], None]]` mapping a
  variant name to a mutation applied to its built `working/` directory, exported
  through `tests/working_corpus/__init__.py`. Register
  `INCOHERENT_VARIANTS["partial-init"] = (_BASE, oracle.LOG_PRESENT)` (a coherent
  baseline spec; reuse `_BASE`) and `_POST_BUILD_MUTATIONS["partial-init"] =
  _remove_log_md`, where `_remove_log_md(working_dir)` calls
  `(working_dir / "log.md").unlink()`. Leave every other `INCOHERENT_VARIANTS`
  entry's `(spec, name)` shape untouched.
- In `tests/corpus_fixtures.py`, inside the `incoherent_tree` fixture's `_build`
  closure (line ~299): after `working = wc.build_working_tree(spec, dest)`, apply
  `mutate = wc.POST_BUILD_MUTATIONS.get(name)` and call `mutate(working)` when
  present, before returning `(spec, working, expected)`. This is the only place
  the mutation runs, so the `partial-init` tree is log-absent on disk exactly
  where the corpus tests read it, and nowhere else.

Why this satisfies the corpus tests:

- `test_every_invariant_name_is_exercised` (`tests/test_working_corpus.py` line
  471) now sees `incoherent_tree("partial-init")[2] == "log-present"`, so the
  exercised set equals `CORPUS_INVARIANT_NAMES` and the assertion stays a true
  `==` (no carve-out).
- `test_each_variant_breaks_exactly_its_invariant` (line 444) holds because the
  `partial-init` tree is a coherent baseline with only `log.md` removed, so the
  oracle fires exactly `("log-present",)`.
- The spec-built agreement suite (`tests/test_novel_state_check_disk.py` line
  132) does **not** exercise `log-present` — it iterates the spec-built corpus
  where `build_working_tree` always writes `log.md` — so it neither breaks nor
  covers the new invariant. Work item 4 adds a dedicated agreement assertion over
  the log-absent tree to restore twin coverage for this one name.

Tests: `test_owned_disk_evidence_names_equal_corpus_subset`
(`tests/test_disk_evidence.py` line 62) stays green (the new name enters both
the production `DISK_EVIDENCE_INVARIANT_NAMES` and the oracle subset in
lockstep). `test_owned_names_equal_corpus_vocabulary`
(`tests/test_validate_state_corpus.py` line 62) stays green untouched (it pins
the eight pure-state names). `test_every_invariant_name_is_exercised` and
`test_each_variant_breaks_exactly_its_invariant` stay green via the new variant.
The Work item 1 disk-evidence tests now pass. Validation: `make all` (run the
corpus suite — `tests/test_working_corpus.py` — and the twin/vocabulary pins
explicitly to confirm all four corpus assertions above).

### Work item 3 (Stage C): `RECREATE_LOG` action and the reconcile repair

Docs to read: design §5.4 (loud reconciliation, no deletion); developers-guide
§"genuinely multi-file mutator" (the D-SELF bracket). Skills: `python-router` →
`python-data-shapes` (the frozen `Reconciliation`/`StrEnum`), `leta`.

- In `novel_ralph_skill/state/reconcile.py`: add `RECREATE_LOG = "recreate-log"`
  to `ReconcileAction`. In `derive_reconciliation`, after the `WORD_COUNTS_MATCH_
  DRAFTS` branch and before the `NONE` fall-through, add: `if LOG_PRESENT in
  fired: return Reconciliation(action=RECREATE_LOG, discrepancies=(LOG_PRESENT,),
  detail="recreating the absent log.md receipt")`. Import `LOG_PRESENT` from
  `disk_evidence`. Update the module docstring precedence list (lines 11-32) to
  insert recreate-log between recount and none, and note that `log-present` is
  **not** refuse-class.
- In `novel_ralph_skill/commands/_reconcile.py`: dispatch `RECREATE_LOG`. Because
  the repair changes no `state.toml`, do **not** route it through the D-SELF
  bracket (which writes state twice). Instead call `_append_recovery_entry(
  working_dir, f"recreate-log: {reconciliation.detail}")` — its append-mode open
  creates `log.md` when absent, so the create and the receipt are one write — then
  return a `_write_outcome(RECREATE_LOG, reconciliation)` (exit 0). Update the
  module docstring dispatch list (lines 9-21).
- `check` needs no change: `_check` already attaches `_render_reconciliation` for
  any fired disk-evidence invariant, so a `log-present` tree gets the
  `reconciliation` payload automatically and exits 4.

Tests: a unit test that `reconcile` over a log-absent tree recreates `log.md`
(now present, non-empty receipt), exits 0, and deletes no other `working/` file;
a test that running `reconcile` twice is idempotent (second run is `NONE`/exit 0).
Validation: `make all`.

### Work item 4 (Stage C, behavioural + e2e)

Docs to read: AGENTS.md §"Python verification and testing"; ADR-006 (e2e POSIX
policy). Skills: `python-router` → `python-testing`; `hypothesis` only if a
property test is warranted (see below).

- Twin agreement for `log-present` (restores the coverage the spec-built suite
  cannot reach — see Work item 2 and the Decision Log): in
  `tests/test_novel_state_check_disk.py`, add a test that builds the log-absent
  tree via the `incoherent_tree("partial-init")` fixture and asserts both the
  production `check_disk_evidence(state, working)` and the oracle
  `corpus_check(spec, working)` fire `log-present` and agree. This is the one
  invariant the existing agreement loop (line 132) never iterates, so it must be
  pinned directly.
- Behavioural: add a scenario to `tests/features/reconcile.feature` — "Given a
  partial-init tree (state.toml present, log.md absent) / When I run reconcile /
  Then log.md is recreated and the command exits 0 / And no working/ file was
  deleted" — and its steps in `tests/steps/reconcile_steps.py`, building the tree
  via `INCOHERENT_VARIANTS["partial-init"]` plus the `_remove_log_md` mutation
  (or directly unlinking `working/log.md` after `build_working_tree`, matching
  the step-file style). Add a `check` scenario asserting exit 4 and a
  `log-present` violation with a `reconciliation` payload (extend
  `tests/features/` or the check BDD if one exists; otherwise a direct `pytest`
  test in `tests/test_novel_state_check_disk.py`).
- e2e: add a case to `tests/test_reconcile_e2e.py` reusing
  `_build_and_install_novel_state` (locked cuprum 0.1.0) — materialise a baseline
  tree under the subprocess cwd, delete `working/log.md`, run the installed
  `novel-state reconcile` (exit 0), then a follow-up `check` (exit 0). This is the
  partial-init recovery running as a real installed command.
- Property test (optional, justified): a parametrised/Hypothesis test over the
  corpus variants asserting `log-present` never co-fires with a refuse-class
  member on the same tree and that `derive_reconciliation` yields `RECREATE_LOG`
  only when no higher-precedence violation fired. Use `hypothesis` only if the
  parametrised form over the fixed corpus is insufficient; the corpus is finite,
  so a parametrised test is likely the right adversary (see `python-verification`).

Tests: behavioural, e2e, optional property. Validation: `make all` (the e2e is
`@pytest.mark.slow`, POSIX-only per ADR-006).

### Work item 5 (Stage D, documentation + snapshots)

Docs to read/update: design §5.4 v1-scope block (lines 534-568). This block
states its correction count **twice** — once as a lead-in number and once as a
numbered list — so both must move in **lockstep** or the canonical design
self-contradicts (the same count-lockstep defect Round 2 caught in the
developers-guide). Re-read lines 534-568 in full first, then make every one of
these edits in the **same commit**:

1. Lines 538-540: the lead-in prose reads "v1's disk-authoritative `reconcile`
   deliberately **narrows** that to the **two** deterministically recomputable
   corrections it can make without fabricating an agent judgement". Change "two"
   → "three". (The word "two" is at line 538; verify by re-reading the sentence
   so "the three deterministically recomputable corrections it can make" parses.)
2. After the existing numbered item 2 ("An uncleared `[pending_turn]`.", lines
   557-560) and **before** the closing "deferred" paragraph (line 562), add a new
   numbered item 3: a `log.md` absent beside a present `state.toml` — the
   partial-`init` bootstrap (`init` writes `state.toml` first, `log.md` second,
   and refuses re-runs) — is detected by the `log-present` disk-evidence
   invariant and repaired by recreating an empty `log.md` and appending a
   recovery receipt. State plainly that `log.md` is recomputable (empty at
   `init`, append-only after), so recreating it fabricates no agent judgement and
   keeps disk authoritative; it deletes nothing, exactly as the `no-deletion`
   constraint requires (§5.4).
3. Re-read the closing "deferred" prose (lines 562-568) after the insertion to
   confirm it still scopes only the *broader* `done.flag`/`compiled.md`
   reconstruction and the `cursor-plan-present` refuse disposition as deferred —
   the new item 3 is **in** scope, so the "deferred" list must not name it.

After these edits, re-read lines 534-568 once more and confirm the lead-in count
("three"), the numbered list (now items 1-3), and the closing "deferred" prose
all agree — no place still says "two" reconcilable corrections.

The developers-guide §"Invariant validation" disk-evidence paragraph
(lines 336-348) states the disk-evidence count **twice** and lists the predicates
once; all three must move to seven in **lockstep**, or the canonical
invariant narrative contradicts itself (line 336 saying seven while line 344 still
says six). Make every one of these edits in the same commit:

1. Line 336: `Six **disk-evidence** invariants` → `Seven **disk-evidence**
   invariants`.
2. Lines 337-341 (the predicate enumeration): add `log-present` (the
   partial-`init` bootstrap detector added by task 2.3.4 — `log.md` absent while
   `state.toml` is present) to the list, so the prose names seven, e.g. extend the
   trailing clause to read `… and \`word-counts-match-drafts\` (…added by task
   2.3.2), and \`log-present\` (the partial-\`init\` bootstrap detector — \`log.md\`
   absent while \`state.toml\` is present — added by task 2.3.4) — need \`working/\`
   contents beyond \`state.toml\``.
3. Line 344: `task 2.3.2's \`check_disk_evidence\` … **implements** all six` →
   `… **implements** all seven` (the same `check_disk_evidence` gains the seventh
   predicate in Work item 2). Verify by re-reading the surrounding sentence so the
   "twin of `validate_state`" clause still parses.
4. Lines 346-347: the paragraph pins `DISK_EVIDENCE_INVARIANT_NAMES` "equal to the
   corpus oracle's disk-evidence subset" but names the pin
   `test_owned_names_equal_corpus_vocabulary` — that test pins the **pure-state**
   vocabulary; the disk-evidence subset is pinned by
   `test_owned_disk_evidence_names_equal_corpus_subset`
   (`tests/test_disk_evidence.py` line 62). Correct the cited test name in the same
   edit so the source-of-truth narrative names the right guardrail (this also
   matches the Constraints "Owned-name vocabulary equality" pin).

Do **not** touch the "eight owned names" / "seven §5.2 invariants" figures
(lines 327, 350-353, 386) or the §5.2 invariant table (lines 355-363): those count
the *pure-state* validator and are unchanged — only the disk-evidence subset grows
by one. After the edits, re-read lines 336-348 to confirm both count statements
say seven and the predicate list names `log-present`.

users-guide §recovery (around lines 194-212) — document that
`reconcile` recreates an absent `log.md` from a crashed `init`. Skills:
`en-gb-oxendict`, `documentation-style-guide` conventions.

- Refresh any affected snapshot (`tests/test_novel_state_mutator_snapshots.py` /
  reconcile snapshots) if the new action appears in a captured envelope; redact
  timestamps/paths per AGENTS.md snapshot rules.

Tests: snapshot refresh; doc gates. Validation: `make all` **and**
`make markdownlint` **and** `make nixie` (markdown changed).

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-3-4`.

1. Confirm branch: `git branch --show-current` → `roadmap-2-3-4`.
2. Work item 1: write the failing tests; `make test` (expect new tests
   failing/xfail-strict, no import errors). Commit.
3. Work item 2a: extract the disk-evidence twins into
   `tests/working_corpus/_oracle_disk.py`; `make all` (expect green, no vocabulary
   change); confirm `wc -l tests/working_corpus/_oracle.py
   tests/working_corpus/_oracle_disk.py` are both under 400. Commit.
4. Work item 2: add the production predicate + corpus twin (in the sibling) +
   post-build mutation registry + `partial-init` variant; `make all` (expect green,
   vocabulary-equality, exhaustiveness, and agreement suites passing). Commit.
5. Work item 3: add `RECREATE_LOG` + reconcile dispatch; `make all`. Commit.
6. Work item 4: behavioural + e2e (+ optional property); `make all`. Commit.
7. Work item 5: docs + snapshots; `make all`, then `make markdownlint`, then
   `make nixie`. Commit.

Each commit must pass all gates before it is made (AGENTS.md). Expected
`make all` tail on success resembles:

```plaintext
... N passed ...
```

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes; the new disk-evidence unit tests fail before
  Work item 2 and pass after; the new reconcile derivation/repair tests fail (or
  xfail-strict) before Work item 3 and pass after; the behavioural scenario and
  e2e pass; the disk-evidence vocabulary pin
  `test_owned_disk_evidence_names_equal_corpus_subset`
  (`tests/test_disk_evidence.py` line 62), the pure-state pin
  `test_owned_names_equal_corpus_vocabulary`
  (`tests/test_validate_state_corpus.py` line 62, unchanged), the corpus
  exhaustiveness test `test_every_invariant_name_is_exercised` and
  `test_each_variant_breaks_exactly_its_invariant`
  (`tests/test_working_corpus.py`), and the spec-built agreement suite all hold,
  and the new partial-init twin-agreement assertion (Work item 4) passes.
- File size: after Work item 2a, `wc -l tests/working_corpus/_oracle.py
  tests/working_corpus/_oracle_disk.py` reports both files under 400; after Work
  item 2's additions `_oracle.py` is still under 400 (AGENTS.md line 24 hard cap).
- Docs lockstep (developers-guide): after Work item 5, developers-guide
  lines 336-348 state the disk-evidence count as **seven** in both places
  (line 336 and line 344), the predicate enumeration names `log-present`, and the
  pin reference reads `test_owned_disk_evidence_names_equal_corpus_subset`; the
  "eight owned names" pure-state figures (lines 327, 350-353, 386) and the §5.2
  table are unchanged.
- Docs lockstep (design §5.4): after Work item 5, the design §5.4 v1-scope block
  (lines 534-568) reads **three** deterministically recomputable corrections in
  the lead-in (line 538-540, "two"→"three") **and** carries a numbered list of
  exactly three items, the third being the `log-present`/recreate-`log.md`
  partial-`init` repair; no sentence in that block still says "two" corrections,
  and the closing "deferred" prose does not name the recreate-`log.md` repair as
  deferred. The lead-in phrase wraps across lines 538-539 ("narrows that to the
  two\ndeterministically recomputable"), so verify the count with a newline-tolerant
  check, e.g.
  `grep -Pzo "narrows\*\* that to the three" docs/novel-ralph-harness-design.md`
  matches and `grep -Pzo "narrows\*\* that to the two" docs/novel-ralph-harness-design.md`
  returns no match after the edit.
- Lint/format/type: `make lint`, `make check-fmt`, `make typecheck` clean
  (rolled up by `make all`).
- Audit: `make audit` clean (no new dependency).
- Markdown: `make markdownlint` and `make nixie` clean for the doc changes.

Quality method: `make all` for code; plus `make markdownlint` and `make nixie`
for the markdown work item. Behaviour is acceptable when the Purpose console
transcript reproduces: a log-absent tree reports `log-present` at exit 4, and
`reconcile` recreates `log.md`, exits 0, and a follow-up `check` exits 0, with no
other `working/` file deleted.

## Idempotence and recovery

All steps are re-runnable. `reconcile` over an already-repaired tree is a no-op
(`ReconcileAction.NONE`, exit 0) — pinned by a Work item 3 test. The repair only
creates `log.md` and appends a receipt; re-running creates nothing further and
deletes nothing. Tests build trees under `tmp_path`, so reruns do not drift the
repository. If a commit's gate fails, fix forward on the same work item before
proceeding; do not advance stages on a red gate.

## Interfaces and dependencies

Use these existing modules; introduce no new dependency.

- `novel_ralph_skill/state/disk_evidence.py`: add
  `LOG_PRESENT: typ.Final = "log-present"`, append it to
  `DISK_EVIDENCE_INVARIANT_NAMES`, and define

  ```python
  def _check_log_present(_state: State, working_dir: Path) -> Violation | None:
      """Return a violation when ``state.toml`` is present but ``log.md`` is absent."""
  ```

  appended last to `_PREDICATES`. The first parameter is unused, so it is named
  `_state` to satisfy Ruff ARG001 (convention: `_check_pending_turn_cleared(
  state, _working_dir)`, `disk_evidence.py` line 193).
- `novel_ralph_skill/state/reconcile.py`: extend

  ```python
  class ReconcileAction(enum.StrEnum):
      ...
      RECREATE_LOG = "recreate-log"
  ```

  and add the `LOG_PRESENT` branch to `derive_reconciliation`, after `RECOUNT`,
  before `NONE`. `log-present` is **not** added to `_REFUSE_CLASS`.
- `novel_ralph_skill/commands/_reconcile.py`: dispatch `RECREATE_LOG` by calling
  `_append_recovery_entry(working_dir, "recreate-log: ...")` then
  `_write_outcome(ReconcileAction.RECREATE_LOG, reconciliation)`; no D-SELF
  bracket (no `state.toml` change).
- `tests/working_corpus/_oracle_disk.py` (new in Work item 2a): the relocated
  six physically-disk-reading predicates (`_check_by_chapter_sum`,
  `_check_manifest_disk_bijection`, `_check_done_flag_without_draft`,
  `_check_compiled_matches_drafts`, `_check_word_counts_match_drafts`,
  `_check_cursor_plan_present`) and their `_disk_*`/`_on_disk_chapter_numbers`
  helpers, re-exported through `_oracle.py`. The pure-spec
  `_check_pending_turn_cleared` is **not** here (it stays in `_oracle.py`'s
  `_SPEC_CHECKS`). The `log-present` twin
  `def _check_log_present(working_dir: Path) -> bool: return (working_dir /
  "log.md").exists()` (with a one-line house-style docstring) is added here in
  Work item 2.
- `tests/working_corpus/_oracle.py`: owns the vocabulary — add `LOG_PRESENT =
  "log-present"`, append it to `CORPUS_INVARIANT_NAMES`, import
  `_check_log_present` from `._oracle_disk`, and wire
  `passed[LOG_PRESENT] = _check_log_present(working_dir)` into `corpus_check`. After
  Work item 2a this file is ~260 lines; the Work item 2 additions keep it under
  the 400-line cap.
- `tests/working_corpus/_variants.py`: a post-build mutation registry

  ```python
  _POST_BUILD_MUTATIONS: dict[str, cabc.Callable[[Path], None]] = {
      "partial-init": _remove_log_md,
  }
  ```

  with `INCOHERENT_VARIANTS["partial-init"] = (_BASE, oracle.LOG_PRESENT)` and
  `def _remove_log_md(working_dir: Path) -> None: (working_dir / "log.md").unlink()`;
  export `POST_BUILD_MUTATIONS` via `tests/working_corpus/__init__.py`.
- `tests/corpus_fixtures.py`: in the `incoherent_tree` `_build` closure, apply
  `wc.POST_BUILD_MUTATIONS.get(name)` to the built `working/` directory before
  returning `(spec, working, expected)`.

Locked external library (verified, no new API): cuprum 0.1.0 — catalogue
construction and absolute-path program allowlisting confirmed in
`cuprum/catalogue.py` (`ProgramCatalogue`, `ProjectSettings`, allowlist gate) and
execution in `cuprum/sh.py` (`sh.make`, `ExecutionContext`, `run_sync`, `capture`,
`.exit_code/.stdout/.stderr`). The e2e reuses `_build_and_install_novel_state`
verbatim.

## Revision note

- Round 2 (2026-06-24): resolved the round-1 blocking implementability defect.
  Adding `log-present` to `CORPUS_INVARIANT_NAMES` would have failed
  `test_every_invariant_name_is_exercised` (`tests/test_working_corpus.py` line
  471) with `missing: {'log-present'}`, because `INCOHERENT_VARIANTS` is a pure
  `spec -> (spec, name)` map and `build_working_tree` always writes `log.md`
  (`_builder.py` line 201). Work item 2 now introduces a post-build mutation
  registry (`_POST_BUILD_MUTATIONS` in `tests/working_corpus/_variants.py`,
  applied in the `incoherent_tree` fixture) and a registered `partial-init`
  variant whose mutation unlinks `working/log.md`, so the exhaustiveness
  assertion stays a true `==` (option (a); option (b), a carve-out, is reserved
  as the escalation fallback). Documented that the spec-built agreement suite
  (`tests/test_novel_state_check_disk.py` line 132) never exercises `log-present`
  (all its trees have `log.md`), and added a targeted twin-agreement assertion in
  Work item 4 over the log-absent tree to restore that coverage. Also fixed three
  advisories: corrected the vocabulary-pin reference to
  `test_owned_disk_evidence_names_equal_corpus_subset`
  (`tests/test_disk_evidence.py` line 62); corrected the Work item 5 doc-edit
  instruction to move only the disk-evidence count "Six" -> "Seven" (the "eight
  owned names" pure-state figure is unchanged); and named the unused predicate
  parameter `_state` to satisfy Ruff ARG001. These changes touch Constraints,
  Risks, Progress, Decision Log, Context, Work items 2/4/5, Validation, and
  Interfaces. Remaining work is unchanged in shape; the corpus mechanism is the
  only structural addition.
- Round 3 (2026-06-24): resolved the two round-2 blocking points.
  (1) **Developers-guide count updated in lockstep.** Round 2 changed only
  line 336 ("Six"→"Seven"), leaving line 344 ("implements all six") contradicting
  it in the same canonical disk-evidence paragraph. Work item 5 now instructs four
  coordinated edits to lines 336-348 in one commit: line 336 "Six"→"Seven", the
  predicate enumeration (lines 337-341) gains `log-present`, line 344 "all
  six"→"all seven", and the mis-named pin reference at lines 346-347
  (`test_owned_names_equal_corpus_vocabulary` →
  `test_owned_disk_evidence_names_equal_corpus_subset`) is corrected. A new
  Validation "Docs lockstep" acceptance criterion pins the post-edit state so the
  source-of-truth narrative no longer self-contradicts.
  (2) **`_oracle.py` cap crossing pre-authorised, not a surprise.**
  `tests/working_corpus/_oracle.py` is 399 lines (`wc -l` confirmed) and Work
  item 2's additions (the `LOG_PRESENT` constant, a `CORPUS_INVARIANT_NAMES` entry,
  the `_check_log_present` predicate, and the `passed[...]` wiring — ~9 lines)
  cross the 400-line AGENTS.md hard cap; a terse docstring alone cannot avoid it.
  `_oracle.py` is now in the file-size watch (Constraints) and the Tolerances
  file-size trigger is rewritten so the crossing does not provoke escalation. A
  new behaviour-preserving Work item 2a extracts the physically-disk-reading
  predicate block into a new `tests/working_corpus/_oracle_disk.py` sibling
  **before** Work item 2, dropping `_oracle.py` below the cap (Round 4 corrects
  the exact move list and the ~145-line / ~260-line figures); the `log-present`
  twin then lands in the sibling and
  only its name plus one wiring line re-enter `_oracle.py`. Progress (new 2a item),
  Concrete steps (renumbered with the 2a step and a `wc -l` check), Risks (two new
  extraction risks), Decision Log (the pre-authorised-extraction decision), Context
  (the new sibling and the `_oracle.py` line count), Interfaces (the sibling),
  Tolerances scope budget (8→10 files for the added module), and Validation
  (file-size acceptance) are updated accordingly. The extraction is the only
  structural addition this round; the `log-present`/`RECREATE_LOG` design is
  unchanged.
- Round 4 (2026-06-24): resolved the two round-3 blocking points; no design
  change, only corrected facts and a doc-lockstep gap.
  (1) **Work item 2a's move list corrected against the actual `_oracle.py`.**
  Round 3's list was factually wrong: it named `_check_pending_turn_cleared`
  (line 244) as one of the "six disk-reading predicates" to move, but that
  predicate reads the **spec** (`return spec.pending_turn is None`) and is a
  member of `_SPEC_CHECKS` (line 368) — a pure-spec twin that must **stay** in
  `_oracle.py` referenced by `_SPEC_CHECKS`. It also **omitted**
  `_check_by_chapter_sum` (line 111), which is a genuine physically-disk-reading
  predicate (`tomllib.loads((working_dir / "state.toml")…)`, wired
  `passed[BY_CHAPTER_SUM] = _check_by_chapter_sum(working_dir)` at line 393). The
  move list is now the real physically-disk-reading set wired into `corpus_check`
  at lines 393-398 (`_check_by_chapter_sum`, `_check_manifest_disk_bijection`,
  `_check_done_flag_without_draft`, `_check_compiled_matches_drafts`,
  `_check_word_counts_match_drafts`, `_check_cursor_plan_present`), with
  `_check_pending_turn_cleared` explicitly excluded. The false docstring claim
  "each predicate remains the disk-reading twin" is replaced: `_check_by_chapter_sum`
  twins the *pure-state* `by-chapter-sum` name (owned by `validate_state`, not in
  `DISK_EVIDENCE_INVARIANT_NAMES`), and the disk-evidence-owned `pending-turn-cleared`
  twin is the one predicate that did **not** move. A new Constraints bullet pins
  the distinction between the physically-disk-reading set and the
  production-owned disk-evidence set so no future reader conflates them. The
  post-2a line-count arithmetic is recomputed from the corrected ~145-line body
  block: `_oracle.py` drops to ~260 (not ~210) and `_oracle_disk.py` is ~170.
  Constraints, Tolerances, Risks, Progress, Decision Log, Context, Work item 2a,
  Interfaces, and Validation were updated to the corrected set and arithmetic.
  (2) **Design §5.4 count-lockstep edit added to Work item 5.** Round 3's Work
  item 5 instructed adding the third reconcilable correction to design §5.4 but
  never changed the lead-in count "two" (line 538-539, "deliberately **narrows**
  that to the **two** deterministically recomputable corrections") to "three" —
  the identical count-lockstep defect Round 2 caught in the developers-guide,
  left unfixed in the design itself. Work item 5 now mandates the "two"→"three"
  edit at line 538 in the same commit, instructs re-reading lines 534-568 so the
  lead-in count, the numbered list, and the closing "deferred" prose agree, and
  a new Validation "Docs lockstep (design §5.4)" acceptance line pins the post-edit
  state (including a `grep` that "two deterministically recomputable" returns no
  match). No work-item shape changed; the `log-present`/`RECREATE_LOG` design is
  unchanged.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
reviews and audits of step 2.3's tasks. Execute each as a small addendum pass —
no plan or design-review cycle: make the change, run `make all` (plus `make
markdownlint`/`make nixie` for Markdown), `coderabbit review --agent`, commit,
and tick the matching roadmap sub-task on merge.

- [x] 2.3.4.1 — Document that `reconcile`'s recreate-log restores an empty
  `log.md` in the users' guide (from review:2.3.4, low). The `log-present`
  detector fires on `log.md` absence and cannot distinguish a clean
  partial-`init` crash from a later loss of a populated log; the `RECREATE_LOG`
  repair always recreates an empty `log.md` and exits 0, which could surprise an
  operator expecting prior receipts back. Add a one-paragraph note to the
  `novel-state` users'-guide section that prior receipts are not recoverable.
  Gate with `make markdownlint` and `make nixie`.
