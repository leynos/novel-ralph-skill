# Re-key `word-counts-cover-drafts` off the on-disk drafted subset

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE (all six work items landed; `make all` green at HEAD)

## Purpose / big picture

Roadmap task 2.3.8 closes the coverage gap ADR 009 deferred. Today, while a
novel is mid-draft, the user-facing `novel-state check` cannot catch a
`[word_counts].by_chapter` table that has lost a drafted chapter's key. The
`word-counts-cover-drafts` detector recomputes `by_chapter` by keying off the
**full chapter manifest** and gives up (returns `None`) on any tree where the
manifest and the on-disk `chapter-NN/` directories are not in exact bijection.
A relaxed drafting subset — manifest `{1, 2, 3}`, on-disk `{1, 2}`, phase
`drafting` — is *always* non-bijective, so the detector is silent for the whole
drafting phase. A key-set drift is therefore invisible until the tree returns
to bijection or reaches `final-pass`/`done`.

After this change, `word-counts-cover-drafts` keys off the **on-disk drafted
subset** during a relaxed drafting subset: every chapter that has an on-disk
`chapter-NN/` directory must have a `by_chapter` key. A drafted chapter whose
key the table omits is flagged mid-draft, and `novel-state reconcile` repairs
it with a `RECOUNT`. A user can observe this end-to-end: build a three-chapter
manifest with only chapters 1 and 2 drafted on disk and phase `drafting`,
delete chapter 2's `by_chapter` key, run `novel-state check` and watch it exit
`4` naming `word-counts-cover-drafts`, run `novel-state reconcile` and watch it
exit `0` writing the missing key, then run `check` again and watch it exit `0`.

The relaxation of `manifest-disk-bijection` (ADR 009), the shared-key
`word-counts-match-drafts` value detector, the strict-default reconcile
precedence, `CORPUS_INVARIANT_NAMES`, and the corpus agreement suites must all
stay green.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

1. **The strict/relaxed split is preserved.** `derive_reconciliation`
   (`novel_ralph_skill/state/reconcile.py`) must keep reading
   `check_disk_evidence` with the strict default so the torn `set-chapters`
   COMPLETE precedence (ADR 008; `tests/test_set_chapters_reconcile.py`, which
   builds its decisive tree with `phase_current="drafting"`) is unchanged. Any
   new relaxed behaviour reconcile needs must be threaded explicitly, never by
   flipping that default. (ADR 009 "Why a flag, not an unconditional predicate
   change"; developers-guide.md lines 776-782.)
2. **`manifest-disk-bijection` relaxation is untouched.** The
   disk-subset-of-manifest relaxation, its drafting-only phase gate, the
   always-firing orphan and contiguity directions, and the `final-pass`/`done`
   re-tightening (ADR 009 "Decision outcome") must not change.
3. **`word-counts-match-drafts` is untouched.** The shared-key value detector
   (`_check_word_counts_match_drafts`, roadmap task 2.3.2; D-WC-SHARED-KEYS)
   compares only the intersection keys and must stay orthogonal to the re-keyed
   coverage detector — neither may double-fire on a tree the other owns.
   (design §5.4 v1 reconciliation scope; developers-guide.md lines 707-726.)
4. **The deliberate-twin discipline holds.** The production cover-drafts
   predicate in `novel_ralph_skill/state/_disk_word_counts.py` and the corpus
   oracle twin in `tests/working_corpus/_oracle_disk.py` stay independent
   re-implementations pinned equal by a twin-agreement test; the oracle never
   imports the production predicate it checks. (developers-guide.md lines
   728-756.)
5. **`CORPUS_INVARIANT_NAMES` and `DISK_EVIDENCE_INVARIANT_NAMES` are
   unchanged.** This task changes *when and how* `word-counts-cover-drafts`
   fires, not the vocabulary. The name set, ordering, and the equality pinned by
   `tests/test_disk_evidence.py::test_owned_disk_evidence_names_equal_corpus_subset`
   must hold. (developers-guide.md lines 595-601, 755.)
6. **No file under `working/` is ever deleted by `reconcile`.** The recount
   rewrites `[word_counts]` only. (design §5.4.)
7. **Reconcile convergence.** After a `RECOUNT` repairs a relaxed-subset cover
   gap, a follow-up `check` on the repaired tree must exit `0` — the detector
   and the repair must agree on the key universe so the detector never re-fires
   on its own repair. (See Decision D2.)
8. **AGENTS.md quality gates.** 400-line file cap, 100% docstring coverage
   (`interrogate`), en-GB Oxford spelling in all prose, comments, and commits.
9. **Documentation is the source of truth.** ADR 009's "Known risks" and
   "Outstanding decisions" sections record this gap as deferred; they must be
   amended to record that 2.3.8 resolved it (or a superseding ADR added), and
   the developers-guide blast-radius prose (lines 784-792) must be corrected.

## Tolerances (exception triggers)

Stop and escalate, documenting the trigger in the Decision Log, when:

- **Scope:** implementation touches more than 10 files or more than ~400 net
  lines of code (excluding tests and docs). The bounded edit set is the two
  cover-drafts predicates, their two callers (`check_disk_evidence` and
  `derive_reconciliation`/`_recount`), the corpus variant module, the affected
  tests, ADR 009, and the developers-guide. A wider blast radius means a
  mistaken mechanism.
- **Interface:** any *public* (non-underscore, exported) signature must change
  beyond adding the keyword-only `relax_drafting` parameter already established
  for the bijection twin. `check_disk_evidence`'s public signature already
  carries `relax_drafting_bijection`; reusing it is in tolerance, adding a
  second public flag is not.
- **Reconcile precedence change:** if making reconcile reach `RECOUNT` on a
  relaxed drafting subset requires re-ordering or re-classifying the existing
  torn `set-chapters` COMPLETE arm or the refuse-class arm in
  `derive_reconciliation` (rather than inserting the scoped, drafting-gated
  pre-arm at the pinned position in Decision D3 — AFTER the set-chapters arm,
  BEFORE the refuse arm, gated on `pending_turn is None` AND fired refuse-class
  `== {manifest-disk-bijection}`), stop and escalate — that is a change to ADR
  008/ADR 009 territory.
- **Dependencies:** any new external dependency. None is expected; cuprum,
  hypothesis, syrupy, and pytest are already locked.
- **Iterations:** tests still failing after 3 focused attempts on one work
  item.
- **Ambiguity:** a second coherent reading of the success criterion emerges
  that materially changes the mechanism (e.g. whether the `extra` direction
  should also fire during a relaxed subset — see Decision D2).

## Risks

    - Risk: Reconcile cannot reach RECOUNT on a relaxed drafting subset.
      derive_reconciliation reads the STRICT bijection
      (reconcile.py line 352), so on a manifest-{1,2,3}/disk-{1,2} subset the
      strict manifest-disk-bijection fires, lands in the refuse-class arm
      (reconcile.py line 365), and returns _refuse(…) before the RECOUNT arm
      (line 372). The naive re-key of only the *detector* would make `check`
      flag the gap but leave `reconcile` REFUSE-ing — contradicting the
      roadmap success criterion "repaired by reconcile via RECOUNT".
      Severity: high
      Likelihood: high (this is the default behaviour today)
      Mitigation: Decision D3 — give reconcile a drafting-gated cover-drafts
      pre-arm that re-keys off the on-disk drafted subset and reaches RECOUNT
      *before* the strict refuse-class arm, without relaxing the strict
      bijection the set-chapters precedence reads. Work item 3 owns this and
      pins it with a behavioural test plus the existing reconcile e2e pattern.

    - Risk: The detector re-fires on its own repair (non-convergence).
      recount_words keys by_chapter off the FULL manifest (wordcount.py D-KEY),
      writing a 0-valued key for every undrafted manifest chapter. If the
      re-keyed detector also fired the `extra` direction (table key absent from
      the drafted subset) during a relaxed subset, the post-RECOUNT table
      {01,02,03} would immediately re-trip on the undrafted key 03.
      Severity: high
      Likelihood: high if the `extra` direction is kept
      Mitigation: Decision D2 — during a relaxed drafting subset the detector
      checks the *missing* direction only (drafted chapter without a table
      key). The symmetric `extra` direction returns at bijection /
      final-pass / done where the full key universe is the manifest. Work item
      1 pins convergence with a check->reconcile->check property/behavioural
      test.

    - Risk: A behavioural-pin test encodes the OLD deferral as a contract.
      tests/test_drafting_bijection_relaxation.py::
      test_cover_drafts_silent_on_relaxed_subset_with_drifted_table currently
      asserts the relaxed verdict on a drifted-table subset is empty — the exact
      behaviour 2.3.8 reverses. Leaving it green would mean the new behaviour
      was not actually wired.
      Severity: medium
      Likelihood: high
      Mitigation: Work item 2 replaces that test with its inverse (the relaxed
      verdict now fires word-counts-cover-drafts on the missing direction and
      stays silent on a coherent subset), and Decision D4 records the contract
      flip.

    - Risk: Twin drift between production and oracle under the new flag.
      The oracle cover-drafts twin (_oracle_disk.py line 202) has the same
      manifest!=on_disk deferral and must gain the same drafting-subset re-key,
      or the twin-agreement test (test_disk_evidence.py line 241) will diverge.
      Severity: medium
      Likelihood: medium
      Mitigation: Work item 4 changes both twins in lock-step and extends the
      relaxed agreement test (modelled on test_drafting_bijection_corpus.py) to
      pin the relaxed cover-drafts production path to the relaxed twin.

    - Risk: 400-line file cap breach in _disk_word_counts.py or
      _oracle_disk.py when the predicates grow the drafting branch.
      Severity: low
      Likelihood: low
      Mitigation: keep the drafting branch to the minimal subset computation;
      _disk_word_counts.py is ~150 lines today. If a cap is approached, extract
      a shared `_drafted_subset_cover_violation` helper rather than inlining.

    - Risk (B1): the reconcile pre-arm pre-empts a torn set-chapters COMPLETE.
      The torn set-chapters COMPLETE arm (reconcile.py lines 361-364) and the
      refuse arm (365-367) sit adjacently. A torn set-chapters turn that is a
      coherent drafting subset (manifest {1,2,3}, on-disk {1}) carrying a
      hand-edited cover gap fires BOTH manifest-disk-bijection (strict) AND the
      re-keyed cover-drafts. If the pre-arm runs before the set-chapters arm it
      RECOUNTs instead of COMPLETEing, silently abandoning the pending-turn
      completion and violating ADR 008. The existing set-chapters tests do not
      catch this: their by_chapter always covers the manifest, so no cover gap
      co-occurs (latent regression).
      Severity: high
      Likelihood: high if position is unpinned
      Mitigation: Decision D3 pins the pre-arm AFTER the set-chapters COMPLETE
      arm and BEFORE the refuse arm. Work item 3 adds a B1 regression test (torn
      set-chapters turn, phase drafting, coherent subset, table omitting a
      drafted key) asserting COMPLETE_PENDING_TURN still wins, not RECOUNT.

    - Risk (B2): the pre-arm masks an uncleared pending turn or a second
      contradiction. The pre-arm sits ahead of both the refuse arm and the
      pending-turn arm (#3). A torn NON-set-chapters pending turn (e.g.
      write-draft) on a coherent drafting subset that also carries a cover gap
      would be pre-empted into a RECOUNT, masking the COMPLETE/ROLLBACK the
      pending-turn arm owes; likewise a co-occurring second refuse-class
      violation would be masked instead of REFUSEd.
      Severity: high
      Likelihood: high if the gate is only (phase, subset, cover-missing)
      Mitigation: Decision D3 gates the pre-arm on `state.pending_turn is None`
      AND fired refuse-class exactly `{manifest-disk-bijection}` (the analogue of
      `_set_chapters_turn_explains_bijection`'s guard). Work item 3 adds a B2
      regression test (torn write-draft pending turn, phase drafting, coherent
      subset, with a cover gap) asserting the pending-turn action (COMPLETE or
      ROLLBACK) wins, not RECOUNT, plus a second-refuse-class co-occurrence test
      (a coherent subset cover gap alongside a contradiction) asserting REFUSE
      still wins.

## Progress

    - [x] Work item 1: re-key the production cover-drafts predicate off the
      on-disk drafted subset under a `relax_drafting` flag and thread it from
      `check_disk_evidence`. DONE (commit 6f539f7). Deviation: the planned home
      for the relaxed unit/property tests (`tests/test_disk_evidence.py`) would
      have breached the AGENTS.md 400-line cap (434 lines), so they live in a new
      `tests/test_cover_drafts_relaxation.py` module; the strict direct-call
      tests in `test_disk_evidence.py` are unchanged. The predicate's relaxed
      gate is `on_disk < manifest and coherent_subset` (plus the drafting flag)
      to satisfy the Pylint `too-many-boolean-expressions` rule. coderabbit
      (1 run) flagged bare asserts; explanatory messages added.
    - [x] Work item 2: flip the relaxation behavioural pin and add the positive
      mid-draft detection / coherence tests. DONE (commit 7f41488). Deviation:
      keeping both replacement tests in `test_drafting_bijection_relaxation.py`
      pushed it to 401 lines (over the 400-line cap), so the contract-flip test
      stays there and the coherence/empty-verdict test moved to
      `tests/test_cover_drafts_relaxation.py`. coderabbit (1 run) flagged only a
      hyphenation typo in the untracked planning review artefact
      (`roadmap-2-3-8.logisphere-review-r1.md`, not part of this work item);
      fixed in place, left uncommitted as out of scope.
    - [x] Work item 3: make `reconcile` reach RECOUNT on a relaxed drafting
      subset cover gap via a pre-arm pinned AFTER the set-chapters COMPLETE arm
      and BEFORE the refuse arm (B1), gated on `pending_turn is None` AND fired
      refuse-class `== {manifest-disk-bijection}` (B2); add the B1 (torn
      set-chapters + cover gap -> COMPLETE) and B2 (torn write-draft + cover gap
      -> not RECOUNT; second contradiction + cover gap -> REFUSE) regression
      tests. DONE (commit prior to this tick). Deviations: (1) `reconcile.py`
      plus the new predicates exceeded the 400-line cap, so the two scoped
      precedence predicates, `_REFUSE_CLASS`, `_RECOMPUTABLE_BASENAMES`, and
      `_missing_declared_paths` were extracted to a new
      `novel_ralph_skill/state/_reconcile_precedence.py` and re-imported into
      `reconcile`; the two pre-arms are funnelled through a single
      `_scoped_precedence_exception` helper to keep `derive_reconciliation`
      within the `too-many-return-statements` (<=6) rule. (2) The B2 write-draft
      pin asserts the pre-arm does NOT RECOUNT and the tree REFUSEs (the strict
      bijection is refuse-class and the refuse arm precedes the pending-turn arm,
      so the plan's worded "pending-turn action wins" is unreachable on a
      strict-non-bijective subset; the load-bearing invariant — the pre-arm never
      masks a pending turn — is preserved and pinned). (3) The relaxed-subset
      reconcile tests live in a new `tests/test_relaxed_subset_reconcile.py`
      module for the 400-line cap. (4) crosshair is not locked in this
      environment; the existing `test_derivation_is_total_*` Hypothesis property
      covers the new branch's totality. coderabbit (1 run): 0 findings.
    - [x] Work item 4: re-key the corpus oracle twin and extend the relaxed
      agreement + corpus variant coverage. DONE (commit 13f129d). The oracle
      twin gained the `relax_drafting` flag (independent re-implementation) and a
      parametrized relaxed twin-agreement test (in
      `tests/test_cover_drafts_relaxation.py`) pins production-vs-oracle on both
      the omitted-key (fires) and covers-set (silent) shapes. Deviation: no new
      `INCOHERENT_VARIANTS` registration was added — the mid-draft shape fires
      strict `manifest-disk-bijection`, so registering it as a cover-drafts
      variant would break the strict `corpus_check` agreement suite (the plan's
      own guidance steers the relaxed agreement through a relaxed loop, not the
      strict path); the dedicated relaxed agreement test covers the shape against
      both twins directly. coderabbit (1 run): 0 findings.
    - [x] Work item 5: entry-point and installed-binary e2e for the mid-draft
      check -> reconcile -> check path. DONE (commit eaa7e19). Added the fast
      entry-point e2e (check exit 4 on `word-counts-cover-drafts`, not
      `manifest-disk-bijection`; reconciliation action `recount` pinning D7;
      reconcile exit 0 re-keying `by_chapter`; re-check exit 0) in a new
      `tests/test_relaxed_subset_e2e.py` module (the 400-line cap; the fast test
      pushed `test_reconcile_e2e.py` to 432 lines). Per Decision D5 / the plan's
      atomicity guidance, NO slow installed-binary variant was added — the fast
      path proves the behaviour and the sibling slow e2es use the broken
      `capture=True` idiom under the locked cuprum 0.1.0. coderabbit (1 run)
      flagged bare asserts (fixed) and a line-wrap in the untracked planning
      review artefact (out of scope, uncommitted).
    - [x] Work item 6: amend ADR 009 and the developers-guide; run the markdown
      gates. DONE (commit 9296803). Amended ADR 009 "Known risks" (first bullet
      now records the 2.3.8 resolution) and "Outstanding decisions" (resolved,
      not deferred); corrected the developers-guide blast-radius prose and the
      §5.4-orthogonality paragraph; narrowed the design §5.4 "v1 reconciliation
      scope" deferral to "outside a relaxed drafting subset". `make markdownlint`
      (0 errors, 257 files) and `make nixie` (all diagrams validated) pass.
      coderabbit (1 run): 0 findings.

## Surprises & discoveries

    - Observation: derive_reconciliation reads the STRICT bijection, so a
      relaxed drafting subset lands in the refuse-class arm before RECOUNT.
      Evidence: reconcile.py lines 347-367 (strict check_disk_evidence call,
      then `refuse = [name for name in fired if name in _REFUSE_CLASS]` with
      MANIFEST_DISK_BIJECTION in _REFUSE_CLASS, reconcile.py lines 101-106).
      Impact: a detector-only change cannot satisfy "repaired by reconcile via
      RECOUNT". Reconcile needs a scoped, drafting-gated cover-drafts pre-arm
      (Decision D3). This is the load-bearing finding of the research pass.

    - Observation: recount_words keys by_chapter off the full manifest, value 0
      for undrafted chapters.
      Evidence: wordcount.py recount_words docstring "keys by_chapter by the
      chapter manifest (one entry per manifest chapter, 0 for a chapter whose
      draft.md is absent or empty)" (Decision Log D-KEY).
      Impact: the re-keyed detector must check the *missing* direction only on a
      relaxed subset or it re-fires on its own repair (Decision D2).

    - Observation: an existing test pins the OLD deferral as a contract.
      Evidence: tests/test_drafting_bijection_relaxation.py
      test_cover_drafts_silent_on_relaxed_subset_with_drifted_table (line 196).
      Impact: must be replaced, not merely supplemented (Work item 2).

    - Observation: the re-keyed cover-drafts can co-occur with the strict
      manifest-disk-bijection AND with a pending turn / a second contradiction on
      one tree, so the reconcile pre-arm position and gate are load-bearing.
      Evidence: on a coherent drafting subset the STRICT bijection always fires
      (reconcile.py uses the strict default, line 352); a torn turn additionally
      fires pending-turn-cleared (disk_evidence.py _check_pending_turn_cleared);
      a torn set-chapters turn is COMPLETEd ahead of the refuse arm by
      _set_chapters_turn_explains_bijection (reconcile.py 361-364). The new
      cover-drafts trigger is independent of all three, so without a pinned
      position and an exact-refuse-class / no-pending-turn gate it would mask
      them (review blocking points B1, B2).
      Impact: Decision D3 pins the pre-arm AFTER the set-chapters arm and BEFORE
      the refuse arm and gates it on `pending_turn is None` AND fired refuse-class
      `== {manifest-disk-bijection}`. Work item 3 adds the B1 and B2 regression
      tests.

    - Observation: "drafted subset" must mean directory-present, not non-empty
      draft.md.
      Evidence: _on_disk_chapter_numbers (_disk_paths.py) keys on the
      chapter-NN/ directory; recount_words writes a `0` key for an absent/empty
      draft (wordcount.py D-KEY); a RECOUNT covers every manifest chapter.
      Impact: keying the detector off directory-present keeps convergence after a
      manifest-keyed RECOUNT (a non-empty filter would re-fire on a present-but-
      empty chapter the recount wrote a `0` key for). Decision D6.

    - Observation: cuprum 0.1.0 SafeCmd.run_sync has no `capture` parameter;
      output capture is via `output=RunOutputOptions(capture=True)`.
      Evidence: cuprum/sh.py SafeCmd.run_sync signature (lines 441-447) takes
      `output, timeout, context, stdin`; empirically `run_sync(capture=True)`
      raises TypeError while `run_sync(output=sh.RunOutputOptions(capture=True))`
      succeeds. Existing slow e2e helpers call `.run_sync(..., capture=True)` —
      a latent TypeError under the locked cuprum.
      Impact: Work item 5 (if it adds an installed-binary subprocess e2e) uses
      `output=sh.RunOutputOptions(capture=True)` and must not copy the broken
      idiom (Decision D5).

## Decision log

    - Decision D1: Reuse the keyword-only `relax_drafting` flag pattern, not a
      new predicate or a phase check inside the predicate.
      Rationale: ADR 009 already established a keyword-only, default-strict
      `relax_drafting` flag on the bijection twin and `relax_drafting_bijection`
      on check_disk_evidence; the command layer already passes
      relax_drafting_bijection=True (novel_state.py line 205). Threading the
      same flag to the cover-drafts predicate keeps the strict/relaxed split in
      one place and leaves reconcile and the corpus agreement suite strict by
      default (Constraint 1). A second public flag is out of tolerance.
      Date/Author: 2026-06-26, planning agent.

    - Decision D2: On a relaxed drafting subset, the re-keyed cover-drafts
      detector checks the MISSING direction only (a drafted on-disk chapter with
      no by_chapter key). The symmetric EXTRA direction (a table key absent from
      the key universe) returns at bijection / final-pass / done, where the key
      universe is the full manifest exactly as today.
      Rationale: recount_words writes a 0-valued key for every undrafted
      manifest chapter (D-KEY), so after a RECOUNT the table legitimately holds
      manifest-declared-but-undrafted keys. Firing `extra` against the drafted
      subset would re-trip on those keys and break reconcile convergence
      (Constraint 7, Risk 2). The drafted subset is a subset of the manifest, so
      a drafted chapter must always have a key, but a manifest-declared key need
      not yet correspond to a draft. The success criterion only requires the
      omit-drafted-chapter direction mid-draft.
      Date/Author: 2026-06-26, planning agent.

    - Decision D3: Reconcile reaches RECOUNT on a relaxed drafting subset cover
      gap via a scoped, drafting-gated cover-drafts pre-arm whose position is
      **pinned**: it runs strictly AFTER the existing torn `set-chapters`
      COMPLETE arm (`reconcile.py` lines 361-364) and strictly BEFORE the
      refuse-class arm (lines 365-367). It does not relax the strict bijection.
      The new pre-arm fires only when ALL of:
      (a) `state.pending_turn is None` — no uncleared `[pending_turn]` (B2);
      (b) `state.phase.current == Phase.DRAFTING`;
      (c) the strict bijection break is a coherent subset (no orphan,
      contiguous — `coherent_subset`) with `on_disk < manifest`;
      (d) the fired refuse-class set is **exactly** `{manifest-disk-bijection}`
      — no second refuse-class member (B2), mirroring
      `_set_chapters_turn_explains_bijection`'s `fired_refuse ==
      {MANIFEST_DISK_BIJECTION}` guard; and
      (e) the re-keyed cover-drafts detector (Work item 1, `relax_drafting=True`)
      reports a missing-direction violation.
      In that exact shape reconcile returns `_recount(...)` ahead of `_refuse`.
      Rationale (position, B1): placing the pre-arm AFTER the set-chapters
      COMPLETE arm means a torn `set-chapters` turn that is a coherent drafting
      subset (the `test_partial_directory_torn_turn_completes` shape: manifest
      `{1,2,3}`, on-disk `{1}`) carrying a hand-edited cover gap still COMPLETEs
      the pending turn (ADR 008) rather than being pre-empted into a RECOUNT that
      silently abandons the completion. Gate (a) is redundant given the position
      for the set-chapters case but is kept explicit so a NON-set-chapters torn
      turn (e.g. `write-draft`) on a coherent drafting subset with a cover gap
      reaches the pending-turn arm (#3) — its COMPLETE/ROLLBACK — rather than
      being masked by the pre-arm (B2). Gate (d) ensures the pre-arm never masks
      a second contradiction (an orphan, a non-contiguous gap, or a
      `compiled-matches-drafts`/`done-flag-without-draft`/`cursor-plan-present`
      that co-occurs), which must still REFUSE. Rationale (verdict): a coherent
      drafting subset is precisely the shape ADR 009 certifies honest, so a
      RECOUNT there does not fabricate agent judgement (design §5.4 "repairs only
      where disk is internally consistent and the state is merely stale"); and it
      makes reconcile (strict) agree with the verdict `check` (relaxed) already
      reports for the same tree (D-SHARED — see D7). The `coherent_subset` gate
      reuses the shared `_classify_bijection` (`_disk_paths.py`) so the coherence
      rule stays single-homed. If this cannot be expressed without re-ordering
      the existing set-chapters or refuse arms, the Tolerance "Reconcile
      precedence change" fires.
      Date/Author: 2026-06-26, planning agent. Revised 2026-06-26 (round 2) to
      pin the pre-arm position (B1) and the no-pending-turn / single-refuse-class
      gate (B2).

    - Decision D4: Replace, do not supplement,
      test_cover_drafts_silent_on_relaxed_subset_with_drifted_table.
      Rationale: it pins the exact deferral 2.3.8 reverses; keeping it green
      would prove the new behaviour was not wired. Its replacement asserts the
      inverse contract (fires on the missing direction mid-draft, silent on a
      coherent subset). The docstring records the supersession and cites this
      task.
      Date/Author: 2026-06-26, planning agent.

    - Decision D5: Verified cuprum API for the installed-binary e2e against the
      LOCKED cuprum 0.1.0 source.
      Rationale: the installed-binary e2e (Work item 5) reuses the existing
      fixture mechanism. The pinned APIs are: `ProgramCatalogue(projects=...)`
      and `ProjectSettings(name, programs, documentation_locations, noise_rules)`
      (cuprum/catalogue.py); `Program` from `cuprum.program` allowlisted via the
      catalogue — cuprum 0.1.0 allowlists any `Program` string including an
      absolute path, the catalogue allowlist being the gate (conftest.py
      `single_program_catalogue` docstring); `sh.make(prog, catalogue=...)(...)`
      builds a `SafeCmd`, and `SafeCmd.run_sync(...) -> CommandResult` carries
      `.exit_code`/`.stdout`/`.stderr` (cuprum/sh.py `CommandResult` lines
      93-123, `SafeCmd.run_sync` lines 441-468); cwd via `ExecutionContext(cwd=)`
      (cuprum/sh.py `ExecutionContext` line 169). The fast entry-point e2e drives
      `novel.main()` through `sys.argv` + `SystemExit` and needs no cuprum
      (test_reconcile_e2e.py pattern).
      VERIFIED CORRECTION (round 2): cuprum 0.1.0 `SafeCmd.run_sync` accepts
      `output`, `timeout`, `context`, `stdin` — it does **not** accept `capture`.
      Output capture is requested via `output=sh.RunOutputOptions(capture=True)`
      (cuprum/sh.py `RunOutputOptions` lines 269-281; `SafeCmd.run_sync` signature
      lines 441-447). Empirically confirmed: `SafeCmd.run_sync(capture=True)`
      raises `TypeError: ... unexpected keyword argument 'capture'`, while
      `SafeCmd.run_sync(output=sh.RunOutputOptions(capture=True))` returns a
      `CommandResult` (exit 0, captured stdout). Several existing slow e2e
      helpers (e.g. `test_reconcile_e2e.py`, `test_console_scripts_e2e.py`,
      `test_novel_state_check.py`) call `.run_sync(context=..., capture=True)` on
      a single `SafeCmd`; that idiom is a latent TypeError under the locked
      cuprum and must NOT be copied. If Work item 5 adds an installed-binary
      subprocess e2e, it uses `output=sh.RunOutputOptions(capture=True)`. (Only
      `Pipeline.run_sync` — cuprum/sh.py lines 509-526 — accepts `capture=`.)
      Date/Author: 2026-06-26, planning agent. Corrected 2026-06-26 (round 2).

    - Decision D6: On a relaxed drafting subset the cover-drafts detector keys
      off the **directory-present** on-disk subset (`_on_disk_chapter_numbers`),
      not "non-empty draft.md". A chapter directory with an absent or empty
      `draft.md` (count `0`) is still "on disk" and must carry a `by_chapter`
      key.
      Rationale (review advisory): the manifest-keyed `recount_words` writes a
      key (value `0` when absent/empty) for every chapter it counts, and a
      RECOUNT covers every manifest chapter, so the post-repair table covers the
      directory-present subset by construction — convergence (Constraint 7)
      holds. A "non-empty" filter would let a present-but-empty-draft chapter
      have no key and break convergence after the RECOUNT writes a `0` key for
      it. The detector docstring must state "drafted means directory-present".
      Date/Author: 2026-06-26, planning agent (round 2, from review advisory).

    - Decision D7: The pre-arm exists so reconcile (STRICT) agrees with the
      verdict check (RELAXED) already reports on the same tree (D-SHARED).
      Rationale: `_check` (`novel_state.py` lines 242-253) builds `violations`
      from `check_disk_evidence(..., relax_drafting_bijection=True)` but builds
      `reconciliation` from `derive_reconciliation` (STRICT). On a relaxed
      drafting subset with a cover gap the relaxed `violations` are exactly
      `["word-counts-cover-drafts"]` (the bijection is suppressed). Without the
      pre-arm, `derive_reconciliation` (strict) would REFUSE on the strict
      bijection, so `check` would report a cover-drafts violation with a
      `reconciliation.action == "refuse"` — a self-contradiction. The pre-arm
      makes `derive_reconciliation` return RECOUNT for that tree, so check's
      reported reconciliation matches the repair reconcile enacts. A Work item 5
      assertion pins `check`'s reported `reconciliation.action == "recount"`
      (not `"refuse"`) for the relaxed-subset cover gap.
      Date/Author: 2026-06-26, planning agent (round 2).

## Outcomes & retrospective

**Complete (2026-06-26).** All six work items landed; `make all` is green at HEAD
(1151 passed, 1 skipped) and `make markdownlint` / `make nixie` pass for the
amended docs. The Purpose scenario holds end-to-end (Work item 5 fast e2e): a
relaxed drafting subset with a missing drafted cover key exits `4` on
`word-counts-cover-drafts` (not `manifest-disk-bijection`) with a `recount`
reconciliation, `reconcile` repairs it via `RECOUNT` (exit `0`), and a re-`check`
exits `0`. The strict reconcile precedence (ADR 008 torn `set-chapters` COMPLETE,
pinned by the B1 regression), the bijection relaxation, `word-counts-match-drafts`,
and the corpus agreement suites are all unchanged.

Retrospective notes:

- The 400-line file cap was the dominant force on layout. Three test modules were
  born from it (`test_cover_drafts_relaxation.py`,
  `test_relaxed_subset_reconcile.py`, `test_relaxed_subset_e2e.py`) and one
  production module (`_reconcile_precedence.py`). The plan's Tolerances anticipated
  this ("extract a shared helper rather than inlining"); the splits stayed within
  the bounded edit set.
- The plan's B2 write-draft expectation ("pending-turn action wins") was
  unreachable as worded: a coherent drafting subset always fires the strict
  bijection, which is refuse-class and precedes the pending-turn arm, so the tree
  REFUSEs. The load-bearing invariant — the pre-arm never masks a pending turn
  into a RECOUNT — is preserved and pinned; the test asserts not-RECOUNT and the
  unchanged strict REFUSE outcome (Work item 3 deviation).
- crosshair is not locked in this environment, so the planned totality
  verification falls back to the existing `test_derivation_is_total_*` Hypothesis
  property, which exercises the new branch.
- No `INCOHERENT_VARIANTS` registration was added for the mid-draft shape: it
  fires strict `manifest-disk-bijection`, so the strict `corpus_check` agreement
  suite would mis-classify it; the dedicated relaxed agreement test covers the
  shape against both twins directly (Work item 4 deviation).
- coderabbit was run once per work item (6 runs total); findings were a
  bare-assert style note (Work items 1 and 5, fixed) and out-of-scope typos in the
  untracked planning review artefact. No rate-limiting occurred.

## Context and orientation

A novelist's working tree lives under `working/`. `working/state.toml` is the
typed record of progress; `working/manuscript/chapter-NN/draft.md` holds each
chapter's prose. The `[chapters]` array in `state.toml` is the **manifest**
(the planned chapter list); the **on-disk** chapter set is the `chapter-NN/`
directories that actually exist. The `[word_counts].by_chapter` table maps each
zero-padded chapter number string (`"01"`) to its token count.

`novel-state check` reads `state.toml` and the disk and reports invariant
violations without writing (exit `4` = actionable finding).
`novel-state reconcile` performs the repair `check` reports, independently
re-deriving it (design §5.4). Disk is authoritative; `state.toml` describes
disk.

The §5.4 disk-evidence detector is `check_disk_evidence` in
`novel_ralph_skill/state/disk_evidence.py`. It runs eight predicates; the two
word-count ones live in `novel_ralph_skill/state/_disk_word_counts.py` (split
out for the 400-line cap and re-exported). The two relevant predicates are:

- `_check_word_counts_match_drafts` — the shared-key **value** divergence
  (roadmap 2.3.2): compares only the intersection of table keys and recount
  keys.
- `_check_word_counts_cover_drafts` — the **key-set coverage** divergence
  (roadmap 2.3.6): compares the full key sets, but **defers** (returns `None`)
  when `manifest != _on_disk_chapter_numbers(working_dir)`.

The bijection relaxation (ADR 009, roadmap 2.1.7) added a keyword-only
`relax_drafting` flag to `_check_manifest_disk_bijection` and
`relax_drafting_bijection` to `check_disk_evidence`. When set and
`state.phase.current == Phase.DRAFTING`, a break whose only direction is
`missing` (a manifest entry without a directory) is accepted: the on-disk set
may honestly be a subset of the manifest. The shared classification helper
`_classify_bijection` in `novel_ralph_skill/state/_disk_paths.py` exposes
`coherent_subset` (no orphan, contiguous manifest) — the exact shape the
relaxation accepts.

The corpus structural oracle (`tests/working_corpus/_oracle.py` and
`tests/working_corpus/_oracle_disk.py`) is an independent re-implementation of
every disk-evidence predicate, pinned equal to production by the twin-agreement
tests in `tests/test_disk_evidence.py`. Corpus *variants* are trees built to
trip exactly one named invariant; the cover-drafts variants are declared in
`tests/working_corpus/_variants.py` (lines 212-219) and built by helpers in
`tests/working_corpus/_reconcile_variants.py`.

`derive_reconciliation` in `novel_ralph_skill/state/reconcile.py` classifies a
tree into a `Reconciliation` (action + payload). It reads `check_disk_evidence`
with the **strict** default (line 352). `MANIFEST_DISK_BIJECTION` is in
`_REFUSE_CLASS` (lines 101-106); `WORD_COUNTS_COVER_DRAFTS` and
`WORD_COUNTS_MATCH_DRAFTS` are in `_RECOUNT_TRIGGERS` (lines 118-121). The
refuse arm (line 365) precedes the recount arm (line 372). `recount_words`
(`novel_ralph_skill/state/wordcount.py`) keys `by_chapter` off the **full
manifest**, writing `0` for an absent draft (Decision Log D-KEY in that module).

The command layer `_disk_evidence_or_state_error` in
`novel_ralph_skill/commands/novel_state.py` (line 205) already passes
`relax_drafting_bijection=True`, so once `check_disk_evidence` threads the flag
to the cover-drafts predicate the user-facing `check` gains the re-keyed
behaviour with no command-layer change.

## Plan of work

Stage A is understanding (this plan). Stages B-D below are split into six
atomic, independently committable, gate-passable work items in dependency
order. Each ends with `make all` (and `make markdownlint && make nixie` for
markdown).

### Work item 1: re-key the production cover-drafts predicate

Implements: design §5.4 (disk-authoritative reconciliation, key-set coverage);
ADR 009 "Outstanding decisions" (the deferred re-key this task discharges);
roadmap 2.3.8 success criterion (keys off the on-disk drafted subset
mid-draft). Constraints 1, 3, 4, 5, 7; Decisions D1, D2.

Docs to read first: design §5.2 (invariant 5), §5.4 (v1 reconciliation scope);
ADR 009 in full (especially "Known risks" and "Outstanding decisions");
developers-guide.md lines 707-756 (the cover-drafts orthogonality and the
deliberate-twin discipline) and 763-792 (the relaxation blast radius).

Skills to load: `python-router` then `python-types-and-apis` (the keyword-only
flag signature) and `python-errors-and-logging` (the predicate returns a
`Violation | None`, no exceptions). `leta` for navigation
(`leta show novel_ralph_skill.state._disk_word_counts._check_word_counts_cover_drafts`,
`leta refs _check_word_counts_cover_drafts`).

Change `_check_word_counts_cover_drafts` in
`novel_ralph_skill/state/_disk_word_counts.py` to take a keyword-only
`relax_drafting: bool = False` parameter. Behaviour:

1. Compute `manifest = {chapter.number for chapter in state.chapters}` and
   `on_disk = _on_disk_chapter_numbers(working_dir)`.
2. If `manifest == on_disk` (bijection): keep today's full symmetric-difference
   check unchanged (missing **and** extra), so the bijection / final-pass /
   done path is byte-for-byte as before.
3. Else, if `relax_drafting` is set and `state.phase.current == Phase.DRAFTING`
   and the break is a coherent subset
   (`_classify_bijection(manifest, on_disk).coherent_subset` and
   `on_disk < manifest`): re-key off the **on-disk drafted subset**, where
   "drafted" means **directory-present** — the chapter numbers
   `_on_disk_chapter_numbers(working_dir)` returns, NOT a "non-empty draft.md"
   filter (Decision D6; review advisory). Build
   `drafted_keys = {f"{n:02d}" for n in on_disk}` and fire only the **missing**
   direction — `missing = drafted_keys - table_keys` — naming
   `WORD_COUNTS_COVER_DRAFTS`. Do **not** fire `extra` here (Decision D2), and
   do **not** key off the manifest-keyed `recount_words` key set (which would
   include undrafted manifest keys and over-fire — review advisory). A
   present-but-empty `draft.md` (count `0`) is still directory-present and must
   carry a key, so convergence holds after the manifest-keyed RECOUNT writes its
   `0` key.
4. Else (a non-subset break, or not drafting, or `relax_drafting` False): defer
   exactly as today (`return None`).

Reuse `Phase` (already imported in `disk_evidence.py`; import into
`_disk_word_counts.py`) and `_classify_bijection` / `_on_disk_chapter_numbers`
from `_disk_paths.py` so the coherence rule stays single-homed (Constraint 4).
For the drafted-subset recount, prefer reusing `recount_words` over only the
drafted chapters, or filter the manifest-keyed `disk_word_counts` result to the
on-disk keys — pick the form that keeps the one counting rule
(`len(text.split())`) single-sourced (D-WORDCOUNT). If the branch pushes the
predicate's complexity up, extract a small `_drafted_subset_cover_violation`
helper in the same module.

Thread the flag from `check_disk_evidence` in
`novel_ralph_skill/state/disk_evidence.py`: lift
`_check_word_counts_cover_drafts` out of `_TAIL_PREDICATES` (exactly as the
bijection predicate is lifted, lines 287-302) so it can receive
`relax_drafting=relax_drafting_bijection`, and call it in its
`DISK_EVIDENCE_INVARIANT_NAMES` position (last) so the union order is
unchanged. Update the head/tail assembly and the module docstrings (lines
51-58) to record that cover-drafts now also takes the relaxation flag.

Tests (added/updated in this work item — unit level):

- In `tests/test_disk_evidence.py`, extend the existing direct-call tests so
  `_check_word_counts_cover_drafts` is called with `relax_drafting=False`
  (unchanged) and add a positive `relax_drafting=True` mid-draft case (manifest
  `{1,2,3}`, on-disk `{1,2}`, phase drafting, table missing `"02"`) asserting
  it fires, plus a coherent-subset case (table covers `{1,2}`) asserting it is
  silent. These pin Decision D2's missing-only semantics.
- A **convergence** property test (hypothesis, `python-verification` ->
  `hypothesis`): for a relaxed drafting subset with a missing drafted key,
  after applying a manifest-keyed recount to the table the re-keyed detector is
  silent (Constraint 7). Build the (manifest, on-disk, missing-key) triple
  constructively from a seed (no rejection sampling — the hypothesis filtering
  trap) over `1 <= drafted < manifest_len <= 4`.

Validation: `make all`. Expect the new unit and property tests to fail before
the predicate change and pass after.

### Work item 2: flip the relaxation behavioural pin

Implements: roadmap 2.3.8 success criterion (flagged mid-draft); ADR 009
supersession of the deferral. Constraint 9; Decision D4; Risk 3.

Docs to read first: `tests/test_drafting_bijection_relaxation.py` head
docstring and the
`test_cover_drafts_silent_on_relaxed_subset_with_drifted_table` body (line 196)
so the replacement inverts exactly the asserted contract.

Skills to load: `python-router` -> `python-testing` (pytest fixtures and
behavioural assertions); `leta` for the helper functions
(`_build_bijection_tree`, `_bijection_verdict`) already in that module.

Replace `test_cover_drafts_silent_on_relaxed_subset_with_drifted_table` with a
test that asserts the new contract. Take the relaxed verdict from
`check_disk_evidence(state, working, relax_drafting_bijection=True)` — the full
detector — NOT the bijection-only `_bijection_verdict` helper (which runs only
`_check_manifest_disk_bijection`); the module already imports
`check_disk_evidence` (review advisory). Assertions:

- A relaxed drafting subset (manifest `{1,2,3}`, on-disk `{1,2}`, phase
  drafting) whose `by_chapter` omits a **drafted** chapter's key (`"02"`)
  yields a relaxed verdict that **contains** `WORD_COUNTS_COVER_DRAFTS` and
  does **not** contain `MANIFEST_DISK_BIJECTION` (the bijection is relaxed).
  Under the strict flag the same tree fires `MANIFEST_DISK_BIJECTION` (the
  missing-directory break) and not cover-drafts (strict cover-drafts still
  defers).
- A coherent relaxed subset whose `by_chapter` covers the drafted set `{1,2}`
  (and may carry the undrafted manifest key `"03"=0`) yields an empty relaxed
  verdict — pinning Decision D2's missing-only direction and convergence.

The replacement docstring cites roadmap 2.3.8 and records that it supersedes
the former Decision-D6 deferral contract. Confirm `make all` then reports the
union-order test, the phase-shape matrix property, and the strict-default tests
in the same module still pass unchanged (the relaxation of bijection is
untouched, Constraint 2).

Validation: `make all`.

### Work item 3: reconcile reaches RECOUNT on a relaxed drafting subset

Implements: design §5.4 ("repairs only where disk is internally consistent and
the state is merely stale"; the same `RECOUNT` repairs the coverage divergence,
roadmap 2.3.6 / 2.3.8); roadmap 2.3.8 success criterion ("repaired by reconcile
via RECOUNT"). Constraints 1, 6, 7; Decision D3; Risk 1.

Docs to read first: ADR 008 (the torn `set-chapters` COMPLETE precedence the
strict bijection drives) and ADR 009 "Why a flag, not an unconditional
predicate change"; `reconcile.py` module docstring (the precedence order) and
`derive_reconciliation` lines 326-385; `_recount` (lines 312-324);
`_set_chapters_turn_explains_bijection` (lines 200-onward) for the established
shape of a scoped precedence exception ahead of the refuse arm.

Skills to load: `python-router` -> `python-errors-and-logging` (the precedence
is total and never raises); `leta` (`leta refs derive_reconciliation`,
`leta refs _recount`). Verification: `python-verification` -> `crosshair` to
confirm `derive_reconciliation` stays total over the new branch (it is pure and
total today; the new branch must not break that).

Add a scoped, drafting-gated cover-drafts pre-arm in `derive_reconciliation`,
modelled on the existing `_set_chapters_turn_explains_bijection` exception that
already sits ahead of the refuse arm (line 361). Implement it as a small pure
predicate (e.g. `_drafting_subset_cover_gap(state, working_dir, fired)`) plus
an arm that calls `_recount`, keeping `derive_reconciliation` readable and the
predicate independently testable.

**Position is pinned (B1).** Insert the new arm strictly AFTER the existing torn
`set-chapters` COMPLETE arm (the
`if pending is not None and _set_chapters_turn_explains_bijection(...)` block,
lines 361-364) and strictly BEFORE the refuse-class arm
(`refuse = [...]; if refuse: return _refuse(...)`, lines 365-367). A torn
`set-chapters` turn that is itself a coherent drafting subset with a cover gap
therefore COMPLETEs (its arm runs first) and is never pre-empted into a RECOUNT
(ADR 008 preserved).

**The gate is exact (B2).** The pre-arm fires only when ALL of:

1. `state.pending_turn is None` — so a torn NON-set-chapters pending turn (e.g.
   `write-draft`) on a coherent subset with a cover gap falls through to the
   pending-turn arm (#3) for its COMPLETE/ROLLBACK rather than being masked;
2. `state.phase.current == Phase.DRAFTING`;
3. the strict bijection break is a coherent subset
   (`_classify_bijection(manifest, on_disk).coherent_subset` and
   `on_disk < manifest`) — the exact shape ADR 009 certifies honest;
4. the fired refuse-class set is **exactly** `{MANIFEST_DISK_BIJECTION}` —
   computed as
   `{name for name in fired if name in _REFUSE_CLASS} == {MANIFEST_DISK_BIJECTION}`,
   the analogue of `_set_chapters_turn_explains_bijection`'s guard — so a
   co-occurring second contradiction (orphan, gap, `compiled-matches-drafts`,
   `done-flag-without-draft`, `cursor-plan-present`) still REFUSEs; and
5. the re-keyed cover-drafts detector (Work item 1, called with
   `relax_drafting=True`) reports a missing-direction violation.

In that shape, return
`_recount(state, working_dir, [WORD_COUNTS_COVER_DRAFTS])`. Because
`recount_words` keys off the full manifest, the RECOUNT writes the missing
drafted key (and `0` for any undrafted manifest chapter), so a follow-up
`check` converges (Constraint 7, pinned by Work item 1's property test). The
strict bijection still fires and still refuses on any **non-subset** break
(orphan, gap, or a non-drafting phase), and the gate keeps the set-chapters
COMPLETE and pending-turn arms intact, so ADR 008's torn `set-chapters`
precedence and every existing refuse path are untouched (Constraint 1). Do
**not** change `_REFUSE_CLASS`, the strict `check_disk_evidence` call, or the
existing arm ordering beyond inserting the new gated pre-arm at the pinned
position; if that is impossible, the "Reconcile precedence change" tolerance
fires.

Tests (this work item; unit / behavioural):

- A positive derivation test in `tests/test_reconcile_derivation.py` (or the
  nearest existing reconcile-derivation module): a relaxed drafting subset
  (manifest `{1,2,3}`, on-disk `{1,2}`, phase drafting, **no** pending turn)
  with a missing drafted cover key (`"02"` omitted) derives
  `ReconcileAction.RECOUNT` carrying the disk-derived `by_chapter` (including
  the drafted key it was missing and the `0` undrafted key), **not** REFUSE.
- **B1 regression test** in `tests/test_set_chapters_reconcile.py` (reusing
  `_torn_spec`): a torn `set-chapters` turn at `phase=drafting` that is a
  coherent subset (manifest `{1,2,3}`, on-disk `{1}`) whose `by_chapter`
  **omits a drafted key** (e.g. drop `"01"`) still derives
  `ReconcileAction.COMPLETE_PENDING_TURN` and, driven through `reconcile`,
  COMPLETEs (exit `0`, creates the missing dirs, clears `[pending_turn]`) — NOT
  RECOUNT. This pins that the pre-arm runs after the set-chapters arm.
- **B2 regression test (pending turn)** in `tests/test_reconcile_derivation.py`:
  a torn NON-set-chapters pending turn (`write-draft`) at `phase=drafting` on a
  coherent subset with a cover gap derives the pending-turn action
  (`COMPLETE_PENDING_TURN` or `ROLLBACK_PENDING_TURN`, per the declared paths),
  NOT RECOUNT. This pins the `pending_turn is None` gate.
- **B2 regression test (second contradiction)**: a coherent drafting subset with
  a cover gap that ALSO carries a refuse-class contradiction (e.g.
  `done-flag-without-draft` via a `done.flag` beside an absent draft, or a
  present-and-diverging `compiled.md`) derives `ReconcileAction.REFUSE`, NOT
  RECOUNT. This pins the exact-`{manifest-disk-bijection}` refuse-class gate.
- The existing **strict** non-subset regressions (orphan directory; manifest
  gap; the existing `set-chapters` COMPLETE fixtures) still REFUSE / COMPLETE
  exactly as today — confirm `tests/test_set_chapters_reconcile.py` stays green.
- Verification: `python-verification` -> `crosshair` over the new predicate /
  `derive_reconciliation` to confirm totality is preserved (it must still
  return a `Reconciliation` for every constructible `State` and never raise).

Validation: `make all`. Expect the positive RECOUNT derivation test and the
three regression tests to fail before the pre-arm (the B1/B2 ones because the
pre-arm does not yet exist or, with a naive insertion, mis-classifies) and pass
after the pinned, gated insertion; every existing refuse/complete test stays
green throughout.

### Work item 4: re-key the corpus oracle twin and extend agreement coverage

Implements: developers-guide.md lines 728-792 (deliberate-twin discipline and
the relaxed agreement suite); ADR 009 (the relaxed agreement pattern).
Constraints 4, 5; Decision D2; Risk 4.

Docs to read first: `tests/working_corpus/_oracle_disk.py`
`_check_word_counts_cover_drafts` (line 202) and
`_check_manifest_disk_bijection` (line 73, the established `relax_drafting`
twin pattern); `tests/test_drafting_bijection_corpus.py` (the relaxed agreement
test shape); `tests/working_corpus/_variants.py` lines 212-219 and
`tests/working_corpus/_reconcile_variants.py` (`cover_omits_drafted_chapter`,
`cover_extra_table_key`).

Skills to load: `python-router` -> `python-testing`; `leta` for the variant
helpers; `python-data-shapes` if a new `WorkingTreeSpec` builder is needed for
the mid-draft subset variant.

Steps:

1. Add a keyword-only `relax_drafting: bool = False` parameter to the oracle's
   `_check_word_counts_cover_drafts` (`_oracle_disk.py` line 202), mirroring
   the production re-key from Work item 1 exactly (missing-only on a coherent
   drafting subset; full symmetric difference at bijection; deferral
   otherwise). Keep it an independent re-implementation — do not import the
   production predicate (Constraint 4).
2. Extend the twin-agreement tests in `tests/test_disk_evidence.py`
   (`test_word_counts_cover_twin_equals_corpus_oracle`, line 241) to also pin
   the **relaxed** path: call both twins with `relax_drafting=True` over a
   relaxed-subset variant and assert they agree, alongside the unchanged strict
   agreement.
3. Add a corpus variant for the mid-draft missing-drafted-key shape. Add a
   `reconcile_variants` builder (e.g.
   `cover_omits_drafted_chapter_mid_draft()`) producing a `phase=drafting`,
   manifest `{1,2,3}`, on-disk `{1,2}` tree with `"02"` omitted from
   `by_chapter`, and register it in `tests/working_corpus/_variants.py`.
   Because the whole-corpus `corpus_check` (`_oracle.py` line 258) runs the
   **strict** twin, drive this variant's relaxed agreement through a relaxed
   loop modelled on `test_drafting_bijection_corpus.py` (call production
   `check_disk_evidence(..., relax_drafting_bijection=True)` and the relaxed
   oracle twin), not through the strict `corpus_check` path, so the strict
   agreement suite and `CORPUS_INVARIANT_NAMES` stay unchanged (Constraint 5).

Validation: `make all`. Expect the relaxed agreement extension to fail before
the oracle re-key and pass after; the strict corpus agreement suite unchanged.

### Work item 5: entry-point and installed-binary e2e

Implements: AGENTS.md e2e rule (a change to externally observable command-line
behaviour); roadmap 2.3.8 success criterion observed end-to-end. Constraint 6;
Decision D5.

Docs to read first: `tests/test_reconcile_e2e.py` (the
`test_entry_point_reconcile_repairs_cover_gap_then_check_clean` fast
entry-point pattern, lines 75-123, and the
`test_entry_point_reconcile_drops_orphan_cover_key_then_check_clean` symmetric
pattern, lines 126-172); `tests/installed_binary_fixtures.py` (the cuprum
installed-binary harness); ADR 006 (the POSIX-only e2e policy and skip guard).

Skills to load: `python-router` -> `python-testing`; `leta` for the fixture and
helpers; the `firecrawl` skill is **not** needed — the only external library is
cuprum, pinned in Decision D5 against the locked 0.1.0 source, and the fast e2e
path uses `novel.main()` directly.

Add a **fast** entry-point e2e in `tests/test_reconcile_e2e.py` mirroring the
existing cover-gap test but on a **relaxed drafting subset**: build manifest
`{1,2,3}`, on-disk `{1,2}`, `phase.current = drafting`, with `"02"` omitted from
`by_chapter`; drive `novel state check` (expect exit `4` / ACTIONABLE_FINDING
naming `word-counts-cover-drafts`, **not** failing on
`manifest-disk-bijection`, and — pinning Decision D7 — the reported
`reconciliation.action == "recount"`, not `"refuse"`), then
`novel state reconcile` (expect exit `0`, action `recount`, `by_chapter`
re-keyed with the missing drafted count and the `0` undrafted key), then
`novel state check` again (expect exit `0`). This is the user-visible proof in
the Purpose section and the D7 check/reconcile-agreement pin.

Add the installed-binary subprocess e2e variant only if an existing
installed-binary reconcile test already exercises the cover-gap path at
bijection; otherwise the fast entry-point e2e plus the installed-binary
reachability test already present is sufficient (do not add a slow wheel-build
test for a behaviour the fast path already proves — AGENTS.md atomicity and the
module-scoped fixture cost). Record the choice in the Decision Log when
implementing. If added, use the cuprum APIs pinned in Decision D5 — in
particular drive capture via `output=sh.RunOutputOptions(capture=True)`, NOT the
`capture=True` kwarg the sibling slow tests use (which raises `TypeError`
under the locked cuprum 0.1.0 — Decision D5) — and apply the ADR 006 POSIX skip
guard. Note that because the surrounding module's existing slow e2es already
use the broken `capture=True` idiom, run any new slow e2e in isolation to
confirm it executes (the pre-existing slow tests may not run cleanly in this
environment).

Validation: `make all` (the e2e runs under the standard suite).

### Work item 6: documentation — amend ADR 009 and the developers-guide

Implements: AGENTS.md documentation-maintenance rules; design §5.4 and ADR 009.
Constraint 9.

Docs to read first: ADR 009 "Known risks and limitations" (lines 154-160) and
"Outstanding decisions" (lines 165-171); developers-guide.md lines 784-792 (the
blast-radius prose that states cover-drafts is "not enforced" during a relaxed
subset); the documentation-style-guide and the en-gb-oxendict convention.

Skills to load: `en-gb-oxendict` (Oxford spelling in prose); `leta`/`grepai`
only if cross-references need locating.

Steps:

1. Amend ADR 009. In "Known risks and limitations", update the first bullet to
   record that 2.3.8 discharged the deferred re-key: during a relaxed drafting
   subset `word-counts-cover-drafts` now keys off the on-disk drafted subset
   (missing direction only) and is repaired by RECOUNT, so the gap no longer
   waits for bijection / final-pass. In "Outstanding decisions", change the
   final paragraph from "deferred to a later roadmap task" to "resolved by
   roadmap task 2.3.8 (see docs/execplans/roadmap-2-3-8.md)". Keep ADR 009's
   bijection-relaxation decisions intact. (Per AGENTS.md, prefer amending the
   ADR with a status note over silently editing a decision; if the reviewer
   prefers a superseding ADR 011, escalate — Tolerance "Ambiguity".)
2. Correct developers-guide.md lines 784-792: cover-drafts is **no longer**
   "not enforced" during a relaxed subset — it re-keys off the drafted subset
   (missing direction), fires mid-draft, and is repaired by RECOUNT. State the
   convergence rule (the manifest-keyed recount writes the undrafted keys, so
   the missing-only detector does not re-fire). Cross-reference ADR 009 and
   roadmap 2.3.8.
3. Update the §5.4 design prose only if it asserts the deferral as a fixed
   property (re-read the "v1 reconciliation scope" paragraph; today it says
   both word-count invariants "defer to manifest-disk-bijection when the
   manifest and the chapter directories disagree" — narrow that to "outside a
   relaxed drafting subset" so the design stays accurate).
4. Wrap prose at 80 columns; run `make fmt` to format markdown tables.

Validation: `make markdownlint` and `make nixie` (and `make all` if any code
docstring changed). Expect both markdown gates to pass.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-3-8`.

Confirm the branch and a clean baseline:

    git branch --show-current   # expect: roadmap-2-3-8
    make all                    # expect: green baseline before any change

Per work item: make the edit, add/adjust its tests, then gate:

    make all

For the markdown-only work item 6:

    make markdownlint
    make nixie

Commit each work item separately with an imperative subject (AGENTS.md):

    git add -A && git commit

Expected transcript shape for the Work item 5 fast e2e (illustrative):

    novel state check     -> exit 4, violations include "word-counts-cover-drafts"
    novel state reconcile -> exit 0, action "recount", by_chapter re-keyed
    novel state check     -> exit 0

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes. New tests fail before their work item's change and
  pass after — in particular the Work item 1 mid-draft detection unit test, the
  convergence property test, the Work item 3 RECOUNT derivation test, the Work
  item 4 relaxed twin-agreement extension, and the Work item 5 fast e2e. The
  replaced behavioural pin (Work item 2) asserts the inverse of the former
  deferral contract.
- Lint/typecheck/docstrings: `make lint`, `make typecheck`, `make check-fmt`,
  and the `interrogate` 100% docstring coverage gate pass (all folded into
  `make all`).
- Audit: `make audit` passes (no new dependency).
- Markdown: `make markdownlint` and `make nixie` pass for ADR 009, the
  developers-guide, and this plan.

Quality method (how we check): run `make all` after each work item, plus the
two markdown gates after the documentation work item. Acceptance is the Purpose
scenario observed end-to-end through the Work item 5 e2e: a relaxed drafting
subset with a missing drafted cover key exits `4` on `word-counts-cover-drafts`,
`reconcile` repairs it via `RECOUNT` (exit `0`), and a re-`check` exits `0`,
while the strict reconcile precedence, the bijection relaxation,
`word-counts-match-drafts`, and the corpus agreement suites stay green.

## Idempotence and recovery

Every step is a code or doc edit under version control; re-running `make all`
is safe and side-effect free. No migrations, no destructive operations —
`reconcile` never deletes a file (Constraint 6). If a work item's gate fails,
revert that work item's edits (`git checkout -- <files>`) and retry; nothing
persists outside the working tree. The recount write is idempotent by
construction (`recount_words` D-KEY: a second run over unchanged drafts yields
a byte-for-byte identical write).

## Interfaces and dependencies

Use only libraries already locked in `pyproject.toml`/`uv.lock`: the standard
library, `tomlkit` (writes), `tomllib` (reads), `hypothesis` (property tests),
`syrupy` (only if a snapshot contract is warranted — none is currently planned),
`pytest`, and `cuprum` 0.1.0 (installed-binary e2e only). No new dependency.

Signatures that must exist at the end:

    # novel_ralph_skill/state/_disk_word_counts.py
    def _check_word_counts_cover_drafts(
        state: State, working_dir: Path, *, relax_drafting: bool = False
    ) -> Violation | None: …

    # novel_ralph_skill/state/disk_evidence.py
    def check_disk_evidence(
        state: State, working_dir: Path, *, relax_drafting_bijection: bool = False
    ) -> tuple[Violation, …]: …  # threads relax_drafting to cover-drafts

    # tests/working_corpus/_oracle_disk.py
    def _check_word_counts_cover_drafts(
        working_dir: Path, *, relax_drafting: bool = False
    ) -> bool: …

`derive_reconciliation(state, working_dir) -> Reconciliation` keeps its public
signature; it gains an internal drafting-gated cover-drafts pre-arm (Decision
D3) ahead of the refuse arm, reusing `_classify_bijection`
(`novel_ralph_skill/state/_disk_paths.py`) for the `coherent_subset` gate and
`_recount` for the payload. The command-layer `check` is unchanged; it already
passes `relax_drafting_bijection=True`.

cuprum 0.1.0 APIs the e2e relies on (verified against the locked source at
`/data/leynos/Projects/cuprum`, Decision D5): `cuprum.ProgramCatalogue`,
`cuprum.ProjectSettings`, `cuprum.program.Program` (allowlisted via the
catalogue; absolute-path programs are accepted),
`cuprum.sh.make(prog, catalogue=...)` building a `SafeCmd`, and
`SafeCmd.run_sync(*, output=..., timeout=..., context=..., stdin=...) -> CommandResult`
with `.exit_code`/`.stdout`/`.stderr`. Capture is requested via
`output=cuprum.sh.RunOutputOptions(capture=True)` — `SafeCmd.run_sync` has NO
`capture` parameter (it raises `TypeError`); only `Pipeline.run_sync` takes
`capture=`. The working directory is set via
`cuprum.sh.ExecutionContext(cwd=...)`. The fast entry-point e2e uses no cuprum.

## Revision note

Round 2 (2026-06-26). What changed and why, in response to the design review
that was not satisfied:

- **B1 (pre-arm position).** Decision D3 now pins the reconcile cover-drafts
  pre-arm to run strictly AFTER the torn `set-chapters` COMPLETE arm
  (`reconcile.py` lines 361-364) and strictly BEFORE the refuse arm (365-367),
  rather than only "before the refuse arm". Work item 3 adds a B1 regression
  test (torn `set-chapters` turn at drafting, coherent subset, table omitting a
  drafted key) asserting `COMPLETE_PENDING_TURN` still wins, not `RECOUNT`. A
  new Risk (B1) and a Surprise record the latent regression the existing
  set-chapters tests cannot catch (their `by_chapter` always covers the
  manifest, so no cover gap co-occurs).
- **B2 (pre-arm gate).** Decision D3 now gates the pre-arm on
  `state.pending_turn is None` AND fired refuse-class
  `== {manifest-disk-bijection}` (the analogue of
  `_set_chapters_turn_explains_bijection`'s guard), so a torn
  non-`set-chapters` pending turn or a co-occurring second contradiction is
  never masked. Work item 3 adds two B2 regression tests (torn `write-draft`
  pending turn + cover gap -> pending-turn action wins; second refuse-class
  contradiction + cover gap -> REFUSE wins). A new Risk (B2) records the
  masking hazard.

Also folded in from the review advisories: Decision D6 pins "drafted subset" to
**directory-present** (not non-empty `draft.md`) and Work item 1 / the
convergence property test now spell out `missing = drafted_keys - table_keys`
over the on-disk subset (never the manifest-keyed recount key set); Work item 2
takes its verdict from
`check_disk_evidence(..., relax_drafting_bijection=True)`; Work item 6 corrects
the ADR 009 line citations; and Decision D7 records the
check/reconcile-agreement rationale the pre-arm serves, pinned by a Work item 5
assertion.

Separately, Decision D5 was corrected against the locked cuprum 0.1.0 source:
`SafeCmd.run_sync` has no `capture` parameter (it raises `TypeError`); capture
is `output=sh.RunOutputOptions(capture=True)`. This affects only the optional
installed-binary e2e in Work item 5; the remaining work is unchanged. None of
these revisions widens the scope or interface tolerances.
