# Relax the manifest-disk bijection during drafting

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DONE

## Purpose / big picture

Today `novel-state check` enforces an exact bijection between the `[chapters]`
manifest in `working/state.toml` and the on-disk `working/manuscript/chapter-NN/`
directories: every manifest entry must have a directory and every directory must
have a manifest entry (design §5.2 invariant 5, implemented by
`_check_manifest_disk_bijection` in
`novel_ralph_skill/state/disk_evidence.py`). Beta testing found this makes
`check` unusable for the entire drafting phase: the manifest holds every planned
chapter the instant chapter planning finishes, but during drafting only the
chapters drafted so far need have a populated directory, so `check` exits 4 on
`manifest-disk-bijection` for the whole drafting run.

After this change, while `[phase].current == drafting`, `novel-state check`
accepts a tree whose on-disk chapter set is a **subset** of the manifest — every
on-disk chapter must still map to a manifest entry, but a manifest entry need not
yet have a directory. The relaxation is one-directional and phase-gated: a draft
on disk with **no** manifest entry (an orphan directory) is still a violation in
every phase, and at `final-pass` and `done` the exact bijection is enforced
again. An author can run `novel-state check` mid-draft and get a clean exit 0
when the tree is honestly a drafting-in-progress tree, while a genuinely broken
tree (an orphan directory, a manifest gap, an extra directory at final-pass) is
still a loud exit 4.

You can observe success by building a mid-drafting tree whose manifest declares
chapters 1..3 but whose disk holds only `chapter-01/`, running `novel-state
check`, and seeing exit 0; then advancing the same tree to `final-pass` and
seeing exit 4 with `manifest-disk-bijection` in `result.violations`.

## Constraints

Hard invariants that must hold throughout implementation.

- **No new external dependency.** This is pure validator logic over the already
  locked stack (Python, `tomlkit`, `cuprum` 0.1.0). cuprum is touched only
  through the **existing** console-scripts e2e harness
  (`tests/test_console_scripts_e2e.py`): a `ProgramCatalogue` built from the
  installed script's **absolute path** (cuprum 0.1.0 allowlists any `Program`
  string, including an absolute path — verified in
  `/data/leynos/Projects/cuprum/cuprum/catalogue.py` `ProgramCatalogue` and
  exercised by that test's docstring at line 108), run via
  `sh.make(prog, catalogue=...).run_sync(context=ExecutionContext(cwd=...),
  capture=True)`. No new cuprum surface is introduced.
- **The reconcile precedence must not change behaviour.**
  `novel_ralph_skill/state/reconcile.py::derive_reconciliation` drives the torn
  `set-chapters` COMPLETE path (ADR 008; design §5.4 item 2) off the **strict**
  bijection firing, and its decisive test
  (`tests/test_set_chapters_reconcile.py::_torn_spec`) builds that tree with
  `phase_current="drafting"`. The relaxation MUST NOT suppress the bijection
  signal `derive_reconciliation` reads (see Decision D1).
- **The corpus agreement suite must stay green unchanged for the strict
  detector.** `tests/test_novel_state_check_disk.py::
  test_union_detector_agrees_with_corpus_oracle` and
  `tests/test_disk_evidence.py` pin the production detector to the corpus oracle
  twin (`tests/working_corpus/_oracle_disk.py`) under the **strict** call. The
  default behaviour of `check_disk_evidence` must remain strict, so those tests
  do not have to change semantics.
- **Deliberate-twin discipline (developers' guide "Invariant validation").** Any
  production predicate change must be mirrored in its oracle twin, and the two
  must remain pinned to agree. The relaxation adds a parallel path; it does not
  let production and oracle drift on the strict path.
- **One vocabulary.** The invariant name stays `manifest-disk-bijection`
  (`disk_evidence.MANIFEST_DISK_BIJECTION`), spelled identically in production
  and oracle; no new public invariant name is introduced (the relaxation changes
  *when* the existing name fires, not the name).
- **`check` writes nothing on any path** (design §3.3). This is a checker change
  only.
- **File-size cap.** Keep every touched module within the AGENTS.md 400-line cap
  (`disk_evidence.py` is currently 301 lines; budget the addition or extract).
- **Prose conventions.** en-GB Oxford spelling (`-ize`/`-yse`/`-our`) in all
  comments, docstrings, ADR, guide prose, and commit messages.

## Tolerances (exception triggers)

- **Scope:** if the implementation requires changes to more than 12 files or
  more than ~350 net lines of code, stop and escalate.
- **Interface:** the only sanctioned public-signature change is adding a
  keyword-only, default-strict parameter to `check_disk_evidence` (Decision D1).
  If any other public signature in `novel_ralph_skill/state/__init__.py` must
  change, stop and escalate.
- **Reconcile behaviour:** if making `check` relax forces any change to
  `derive_reconciliation`'s observable output on any existing reconcile test,
  stop and escalate — that means the strict/relaxed split (D1) has leaked.
- **Iterations:** if the corpus agreement suite or the reconcile suite still
  fails after 3 focused attempts, stop and escalate.
- **Ambiguity:** if drafting-phase semantics for a tree that is *both* a subset
  *and* carries an orphan directory cannot be expressed as "orphan still fires,
  missing-directory relaxed" without a name collision, stop and present options.

## Risks

```plaintext
    - Risk: The relaxation suppresses the bijection for the torn set-chapters
      reconcile path (which runs at phase=drafting), silently flipping a
      COMPLETE into a NONE/REFUSE.
      Severity: high
      Likelihood: high (the existing reconcile test uses phase=drafting)
      Mitigation: D1 — relaxation is a keyword-only, default-strict flag on
      check_disk_evidence; _check() passes the relaxed flag, derive_reconciliation
      keeps the strict default. A regression test asserts the torn set-chapters
      tree still COMPLETEs.

    - Risk: The existing `manifest-extra-entry` INCOHERENT corpus variant is built
      on the drafting-phase _BASE, so under a naive relaxation it would stop being
      a violation and break the corpus agreement suite.
      Severity: high
      Likelihood: high
      Mitigation: The agreement suite calls check_disk_evidence with the default
      (strict) flag, so `manifest-extra-entry` stays a strict violation there. The
      relaxed behaviour is exercised only through _check() and a dedicated
      relaxed-detector test (and, if added, a positive relaxed corpus case keyed to
      the relaxed oracle path), never through the strict agreement loop.

    - Risk: Phase is read from a malformed `state.phase.current` and the relaxation
      raises or mis-classifies a non-drafting tree.
      Severity: medium
      Likelihood: low
      Mitigation: the relaxation predicate compares `state.phase.current ==
      Phase.DRAFTING` (a StrEnum identity), is total, and a Hypothesis property
      sweeps every phase × tree-shape combination.

    - Risk: The orphan-direction signal and the missing-directory-direction signal
      are entangled in the single `manifest == on_disk` equality, so relaxing one
      direction accidentally relaxes the other.
      Severity: medium
      Likelihood: medium
      Mitigation: split the predicate's verdict into the two directions
      (disk⊄manifest = orphan; manifest⊄disk = missing-dir) and relax only the
      missing-dir direction under drafting (Decision D2); property test pins both
      directions per phase.

    - Risk: The relaxation's blast radius is wider than "bijection only": because
      `_check_word_counts_cover_drafts` already defers (returns None) whenever
      `manifest != on_disk`, a relaxed subset means cover-drafts is not enforced
      during drafting, so an author could trust a clean `check` over a tree whose
      `by_chapter` key set has drifted, and the drift surfaces late at final-pass.
      Severity: medium
      Likelihood: medium
      Mitigation: D6 — this is an accepted, documented boundary, not a new gap:
      cover-drafts ALREADY deferred on every subset tree under the strict detector
      (it has never fired on a subset), so the relaxation only removes the louder
      bijection signal that masked the deferral; the recount is untrustworthy off
      a non-bijective manifest by design. ADR 009 enumerates cover-drafts as an
      invariant whose enforcement changes under the relaxation, and Work item 2
      adds a test pinning that cover-drafts is silent on a relaxed subset and that
      this is the intended boundary (cover-drafts re-enforces once the tree returns
      to bijection and at final-pass/done).
```

## Progress

```plaintext
    - [x] Work item 1: ADR 009 recording the phase-gated bijection relaxation.
      DONE — docs/adr-009-drafting-bijection-relaxation.md created (ADR 008 shape;
      enumerates the two-invariant blast radius, the strict/relaxed split, and the
      §4.3 re-tightening), linked into docs/contents.md. markdownlint + nixie +
      make all green. CodeRabbit on this item raised only planning-doc style nits
      against the execplan/review artefacts; the major "flag name" nit is a false
      positive — the plan deliberately names the predicate kwarg `relax_drafting`
      and the public `check_disk_evidence` flag `relax_drafting_bijection`
      (sanctioned public name, Tolerances/Interfaces), which is internally
      consistent.
    - [x] Work item 2: split the bijection predicate into its two directions and
      add the phase-gated relaxation behind a default-strict flag on
      check_disk_evidence; lift the bijection out of the _PREDICATES loop and call
      it first (preserving DISK_EVIDENCE_INVARIANT_NAMES order); wire _check() to
      relax and derive_reconciliation to stay strict; pin the cover-drafts boundary
      (D6) and the union-order preservation with tests.
      DONE. disk_evidence.py: bijection split into orphans/missing/contiguous,
      keyword-only relax_drafting flag, lifted out of the loop into
      _TAIL_PREDICATES + head-first wiring; check_disk_evidence gains
      relax_drafting_bijection=False. novel_state.py _disk_evidence_or_state_error
      passes True; reconcile.py keeps the strict default with a D1/ADR 009 comment.
      New tests in tests/test_drafting_bijection_relaxation.py (subset/orphan/
      non-contiguous/terminal-phase, cover-drafts D6 boundary, union-order, and a
      Hypothesis phase x shape matrix). Deviation: the ADR-009 unit tests were
      placed in a NEW module rather than extending test_disk_evidence.py because the
      additions breached the 400-line cap; disk_evidence.py stayed in place (no
      sibling extraction needed). Three command-driving suites changed behaviour as
      designed — manifest-extra-entry at drafting now exits 0 via check, so
      test_novel_state_check_disk swaps the bijection exit-4 row to the orphan
      variant and adds an exit-0 case; test_reconcile_refuse and
      test_reconcile_integration exclude manifest-extra-entry from the
      both-commands-refuse / action-agreement loops and gain dedicated strict/relaxed
      split tests. test_set_chapters_reconcile docstring extended to name D1.
      make all green; CodeRabbit: one trivial + one minor (a wrong inline comment in
      the non-contiguous branch), both fixed.
    - [x] Work item 3: corpus oracle twin + positive corpus case asserting the
      FULL relaxed verdict is empty on a coherent drafting subset; property test
      over phase × tree-shape.
      DONE. The oracle twin _oracle_disk._check_manifest_disk_bijection gains a
      keyword-only relax_drafting flag mirroring the production split (reads
      [phase].current from the materialised state.toml); the strict default the
      agreement suite calls is unchanged. New ChapterSpec.write_directory field
      (default True, so existing trees stay byte-identical) lets the builder skip a
      REAL drafted chapter's directory — a genuine planned-but-undrafted chapter in
      the manifest but absent on disk, distinct from manifest_only_numbers'
      placeholder. tests/test_drafting_bijection_corpus.py adds the positive
      drafting-subset case (full relaxed verdict (); strict fires exactly
      manifest-disk-bijection) and a relaxed agreement test over
      drafting/final-pass/done. Note: the phase × tree-shape property test landed in
      WI2 (test_relaxed_bijection_phase_shape_matrix) where the predicate-level
      shapes live; this item's property obligation is met there. make all green;
      CodeRabbit: 0 findings.
    - [x] Work item 4: e2e + users'/developers' guide documentation.
      DONE. tests/test_drafting_bijection_e2e.py adds two installed-script e2e
      cases through the module-scoped installed_novel_state fixture and a cuprum
      ProgramCatalogue: a drafting subset (manifest {1,2,3}, on-disk {1,2} via the
      new write_directory=False chapter) exits 0 with no reconciliation key, and the
      same tree at final-pass exits 4 with manifest-disk-bijection in
      result.violations. Both reuse @pytest.mark.slow + @pytest.mark.timeout(180)
      and the ("check") subcommand argv. users-guide.md annotates the
      manifest-disk-bijection bullet with the drafting subset rule and adds a worked
      example; developers-guide.md annotates the §5.2 invariant-5 table row and adds
      a paragraph on the relaxation, the flag, the strict/relaxed split, the oracle
      twin, and the cover-drafts (D6) blast radius. make all + markdownlint + nixie
      green; CodeRabbit: one minor (envelope assertions want failure context), fixed.
```

## Surprises & discoveries

```plaintext
    - Observation: `set-chapters` (commands/_set_chapters.py::set_chapters,
      step 8) creates ALL manifest directories at once, so a freshly-planned tree
      is already in exact bijection — the mid-draft subset arises later, as the
      author drafts chapter by chapter and the directory set lags the manifest, or
      via a workflow that does not pre-create every directory.
      Evidence: `_write_manifest_turn` mkdirs each chapter dir; the roadmap entry
      says "only the drafted-so-far chapter-NN/ directories exist".
      Impact: the relaxation must accept disk ⊂ manifest regardless of how the
      subset arose; it is a `check`-verdict change, not a `set-chapters` change.
      `set-chapters` is out of scope for this task.

    - Observation: the torn `set-chapters` reconcile test builds its tree with
      `phase_current="drafting"`.
      Evidence: tests/test_set_chapters_reconcile.py line 125.
      Impact: a naive phase-gated relaxation inside the bijection predicate would
      break the reconcile precedence; hence the strict/relaxed split (D1).

    - Observation: the existing `manifest-extra-entry` INCOHERENT variant is
      `dc.replace(_BASE, manifest_only_numbers=...)` and `_BASE` is the drafting
      baseline (`COHERENT_BASELINE = PHASE_STATES["drafting"]`).
      Evidence: tests/working_corpus/_variants.py line 145;
      tests/working_corpus/_library.py line 118.
      Impact: that variant is a manifest-entry-without-directory during drafting —
      exactly the case the relaxation now accepts. The strict agreement suite keeps
      it as a violation (strict call); the relaxed path treats it as coherent.

    - Observation (WI2): three command-DRIVING suites assert check exits 4 over
      ``manifest-extra-entry`` and so flip under the relaxation, beyond the corpus
      agreement suite the plan named. They are NOT strict-detector tests; each
      drives the real ``check``/``reconcile`` commands, so the relaxation correctly
      changes their expectation.
      Evidence: tests/test_novel_state_check_disk.py
      (test_disk_evidence_tree_exits_four_with_reconciliation),
      tests/test_reconcile_refuse.py (_REFUSE_VARIANTS, both-commands refuse), and
      tests/test_reconcile_integration.py (test_check_and_reconcile_actions_agree).
      Impact: handled by (a) swapping the bijection exit-4 coverage to the orphan
      ``draft-without-manifest-entry`` variant and adding an exit-0 case; (b)
      excluding ``manifest-extra-entry`` from the both-commands-refuse and
      action-agreement loops; and (c) adding dedicated strict/relaxed split tests
      (manifest-extra-entry: check exits 0, reconcile still REFUSEs). The strict
      ``check_disk_evidence``/``derive_reconciliation`` suites
      (test_disk_evidence, test_reconcile_derivation) are unchanged.
```

## Decision log

```plaintext
    - Decision: D1 — add a keyword-only `relax_drafting_bijection: bool = False`
      parameter to `check_disk_evidence`; `_check()` passes `True`,
      `derive_reconciliation` keeps the default `False` (strict).
      Rationale: `derive_reconciliation` reads `check_disk_evidence`'s output and
      drives the torn `set-chapters` COMPLETE off the strict bijection firing at
      phase=drafting. A flag with a strict default leaves reconcile and the corpus
      agreement suite untouched while letting only the user-facing checker relax.
      Alternative rejected: phase-gating inside the predicate unconditionally —
      breaks reconcile. Alternative rejected: a separate `check_disk_evidence_relaxed`
      function — duplicates the eight-predicate assembly; a flag is smaller.
      Date/Author: 2026-06-25, planning agent.

    - Decision: D2 — classify the bijection break into two directions inside
      `_check_manifest_disk_bijection`: `on_disk ⊄ manifest` (an orphan directory)
      and `manifest ⊄ on_disk` (a manifest entry without a directory), plus the
      contiguity-from-1 check on the manifest. The relaxation suppresses ONLY the
      "manifest entry without a directory" direction, and ONLY when
      `state.phase.current == Phase.DRAFTING`. Contiguity and orphan directions
      always fire.
      Rationale: the roadmap's success criterion is one-directional ("disk subset
      of manifest" passes; "on-disk chapter absent from the manifest" still flags).
      Splitting the verdict keeps the orphan and contiguity signals loud while the
      missing-directory signal relaxes. NOTE: relaxing the missing-directory
      direction also makes `word-counts-cover-drafts` un-enforced during a relaxed
      subset, because that predicate already defers on `manifest != on_disk`; see
      D6 for the full analysis. D2's "split the verdict" claim is about the
      bijection predicate's two directions only — it does NOT assert the other
      seven predicates are wholly untouched; D6 documents the one (cover-drafts)
      that is.
      Date/Author: 2026-06-25, planning agent.

    - Decision: D3 — the relaxation is gated on `Phase.DRAFTING` only;
      `chapter-planning` (where `set-chapters` runs) and `final-pass`/`done` keep
      the exact bijection. This matches the roadmap ("tightening back to exact
      bijection at final-pass and done") and design §5.4 (the manifest⇄directory
      bijection is the ordering guarantee `novel-compile` relies on, §4.3, which
      must hold before the final compile).
      Rationale: the subset is only honest while chapters are still being drafted.
      At final-pass every planned chapter must exist on disk, so the exact
      bijection is the correct gate.
      Date/Author: 2026-06-25, planning agent.

    - Decision: D6 — the relaxation's true blast radius includes
      `word-counts-cover-drafts`, and this is an ACCEPTED, documented boundary,
      not an accident. `_check_word_counts_cover_drafts`
      (`_disk_word_counts.py` lines 128-130) returns `None` (defers) whenever
      `manifest != _on_disk_chapter_numbers(working_dir)`, because it recomputes
      `by_chapter` by keying off the manifest and a non-bijective manifest makes
      that recount untrustworthy; that deferral is the predicate's own design
      (its docstring, lines 119-127, states it defers to the bijection signal so
      the two do not double-fire). A relaxed drafting subset ALWAYS satisfies
      `manifest != on_disk` (that is precisely what "subset" means), so for any
      tree the relaxation newly accepts, `word-counts-cover-drafts` was ALREADY
      deferring under the strict detector — it has never fired on a subset tree.
      Empirically: the `manifest-extra-entry` corpus tree (manifest `{1,2,3,4}`,
      table keys `{01,02,03}`, recount keys `{01,02,03,04}`) fires
      `manifest-disk-bijection` ONLY; cover-drafts already defers there under
      strict (`tests/test_disk_evidence.py` agreement). So the relaxation does NOT
      "disable a firing check"; it removes the louder `manifest-disk-bijection`
      signal that previously masked the deferred-and-silent cover-drafts state.
      The net effect: during a relaxed drafting subset, the `by_chapter`
      key-set-coverage check (cover-drafts) is INTENTIONALLY not enforced — it is
      re-enforced the moment the tree returns to bijection (every drafted chapter
      gets its directory) and again at `final-pass`/`done` where the strict
      bijection is mandatory. This is the correct boundary: cover-drafts is a
      stale-table check whose recount is only trustworthy under bijection, so it
      cannot meaningfully run on a subset anyway. ADR 009 enumerates this
      explicitly (every invariant whose firing changes under the relaxation), and
      a test pins it (cover-drafts is silent on a relaxed subset, and the boundary
      is the intended one). Alternative rejected: also relax cover-drafts to key
      off the on-disk drafted subset rather than the manifest — that is a separate
      detector redesign (roadmap 2.3.6 territory), out of scope here, and would
      change cover-drafts semantics under bijection too.
      Date/Author: 2026-06-25, planning agent.

    - Decision: D7 — the strongest alternative (Wafflecat, review r1) was to keep
      `check_disk_evidence` a single pure strict function and have the command
      layer (`_check`) drop the `manifest-disk-bijection` violation when
      phase==drafting and the only broken direction is missing-directory. It was
      rejected because the `Violation` detail is a free-text string
      (`disk_evidence.py` lines 127-132), so the command layer cannot tell a
      missing-direction-only break from an orphan break without re-deriving the
      direction (re-reading disk and the manifest) or the predicate exposing
      structured direction data on `Violation` — either of which is a larger
      surface change than a default-strict flag. The flag keeps the
      direction-classification logic in the one place that already holds the sets
      (`_check_manifest_disk_bijection`) and adds exactly one keyword-only
      parameter. The oracle-twin and relaxed-agreement churn the flag signs up for
      (Work item 3) is bounded and mirrors the production split one-to-one.
      Date/Author: 2026-06-25, planning agent.

    - Decision: D4 — record the relaxation in a new ADR (ADR 009) rather than only
      in the guides, because the roadmap entry explicitly says "Record an ADR" and
      because relaxing a §5.2 invariant during a phase is a controlling decision
      future readers must not mistake for a bug (mirrors ADR 008's standing).
      Date/Author: 2026-06-25, planning agent.
```

## Outcomes & retrospective

Outcome: achieved, all four acceptance behaviours proven by tests. A mid-drafting
manifest subset exits 0 (unit, corpus, and installed-script e2e); an orphan
directory and a non-contiguous manifest still exit 4 in every phase; the same
subset at final-pass/done exits 4 with `manifest-disk-bijection`; the torn
`set-chapters` drafting tree still derives COMPLETE_PENDING_TURN (reconcile reads
the strict bijection, D1); the cover-drafts boundary (D6) is pinned (a drifted
table on a relaxed subset still yields an empty relaxed verdict, the same tree
firing only `manifest-disk-bijection` under strict); and the exit-0 e2e tree
carries no `reconciliation` key. The strict corpus agreement suite
(`test_union_detector_agrees_with_corpus_oracle`) and the strict
`derive_reconciliation` suites are unchanged because `check_disk_evidence`
defaults to strict; only the user-facing `check` passes
`relax_drafting_bijection=True`.

Deviations from the plan, all benign:

- The ADR-009 predicate-level unit tests and the phase x tree-shape Hypothesis
  property landed in a NEW module (`tests/test_drafting_bijection_relaxation.py`)
  rather than extending `tests/test_disk_evidence.py`, because the additions
  breached the AGENTS.md 400-line cap; `disk_evidence.py` itself stayed in place
  (no sibling extraction needed — it sits at ~370 lines).
- The corpus-loop assets landed in a second new module
  (`tests/test_drafting_bijection_corpus.py`), and the e2e in a third
  (`tests/test_drafting_bijection_e2e.py`), reusing the module-scoped
  `installed_novel_state` fixture rather than rebuilding the
  `test_console_scripts_e2e.py` harness.
- Three command-DRIVING suites beyond the corpus agreement suite the plan named
  changed their expectations as designed (manifest-extra-entry at drafting now
  exits 0 via check while reconcile still REFUSEs); each gained a dedicated
  strict/relaxed split test. See Surprises & discoveries (WI2).
- A new `ChapterSpec.write_directory` field (default True, byte-identical for
  existing trees) was added so the positive corpus fixture models a REAL planned-
  but-undrafted chapter absent on disk, as the plan's Work item 3 step 3 directed.

## Context and orientation

The harness is a set of deterministic Python commands over a `working/` project
tree. State lives in `working/state.toml`; the manuscript lives under
`working/manuscript/chapter-NN/` (zero-padded), each holding `draft.md` and, when
complete, `done.flag` (design §5.1). The compiled manuscript is
`working/manuscript/compiled.md`.

`novel-state check` runs two verdict producers and unions them
(`novel_ralph_skill/commands/novel_state.py::_check`, lines 210-255):

- `novel_ralph_skill.state.validate_state` — the §5.2 **pure-state** invariants,
  decidable from `state.toml` alone.
- `novel_ralph_skill.state.check_disk_evidence`
  (`novel_ralph_skill/state/disk_evidence.py`) — the §5.4 **disk-evidence**
  invariants, comparing `state.toml` against the `working/` tree. It owns eight
  predicates assembled in `_PREDICATES` (lines 264-273) and returns an ordered
  `tuple[Violation, ...]`. The bijection predicate is
  `_check_manifest_disk_bijection` (lines 112-133): it builds `manifest =
  {chapter.number for chapter in state.chapters}` and `on_disk =
  _on_disk_chapter_numbers(working_dir)`, then fires
  `MANIFEST_DISK_BIJECTION` unless `manifest == on_disk` and the manifest is
  contiguous from 1.

The phase enum lives in `novel_ralph_skill/state/phase.py`
(`Phase`, a `StrEnum`); `Phase.DRAFTING == "drafting"`. The parsed phase is
`state.phase.current` (`PhaseState.current`, `novel_ralph_skill/state/schema.py`).

**Coupling with `word-counts-cover-drafts` (load-bearing — read before
implementing).** One other disk-evidence predicate observes the manifest⇄disk
relationship: `_check_word_counts_cover_drafts`
(`novel_ralph_skill/state/_disk_word_counts.py` lines 102-143). Its first guard
(lines 128-130) is `if manifest != _on_disk_chapter_numbers(working_dir): return
None` — it **defers** (silently coherent) on any tree where the manifest and
on-disk directory sets differ, because it recomputes `by_chapter` by keying off
the manifest and a non-bijective manifest makes that recount untrustworthy (its
docstring, lines 119-127, says so explicitly: it defers to the bijection signal
so the two predicates do not double-fire). A relaxed drafting **subset** has
`manifest != on_disk` by definition, so cover-drafts already deferred on every
such tree under the strict detector — it has never fired on a subset. The
relaxation therefore does not silence a *firing* check; it removes the louder
`manifest-disk-bijection` signal that previously sat in front of the already-silent
cover-drafts deferral. The consequence is real and must be documented (ADR 009,
D6): during a relaxed drafting subset the `by_chapter` key-set-coverage check is
not enforced. It re-enforces the instant the tree returns to bijection (every
drafted chapter has its directory) and at `final-pass`/`done` where the strict
bijection is mandatory. The other six disk-evidence predicates
(`cursor-plan-present`, `done-flag-without-draft`, `compiled-matches-drafts`,
`pending-turn-cleared`, `word-counts-match-drafts`, `log-present`) do not read the
manifest⇄disk equality and are genuinely unaffected — `word-counts-match-drafts`
compares only **shared** chapter keys (`_disk_word_counts.py` lines 92-96), so it
stays clean on a subset whose present drafts match the table.

`novel_ralph_skill/state/reconcile.py::derive_reconciliation` (lines 323-382)
also calls `check_disk_evidence(state, working_dir)` (line 345) and uses the
`manifest-disk-bijection` firing to drive the scoped torn-`set-chapters`
COMPLETE precedence (`_set_chapters_turn_explains_bijection`, lines 199-236;
`_complete_set_chapters_turn`, lines 281+). ADR 008 records this. The decisive
reconcile test (`tests/test_set_chapters_reconcile.py`) builds its torn tree with
`phase_current="drafting"` (line 125), so the bijection MUST keep firing strictly
for that caller.

The corpus structural oracle (an **independent** re-implementation used as a
cross-check) lives in `tests/working_corpus/`. Its bijection twin is
`tests/working_corpus/_oracle_disk.py::_check_manifest_disk_bijection`
(lines 73-85). The agreement test
`tests/test_novel_state_check_disk.py::test_union_detector_agrees_with_corpus_oracle`
pins production (strict) to the oracle (strict) on every corpus tree. Corpus
variants are defined in `tests/working_corpus/_variants.py`; the relevant ones
are `manifest-extra-entry` (a manifest entry without a directory, on the drafting
`_BASE`) and `draft-without-manifest-entry` (an orphan directory). Coherent
per-phase baselines come from `tests/working_corpus/_library.py`
(`PHASE_STATES`, `COHERENT_BASELINE`); `_drafting_spec` produces the `final-pass`
and `done` baselines with a fully-populated manifest and all directories present.

Terms used in this plan:

- **Bijection (strict):** manifest set equals on-disk set, manifest contiguous
  from 1.
- **Subset relaxation:** on-disk set ⊆ manifest set (every directory maps to a
  manifest entry; some manifest entries may lack a directory).
- **Orphan direction:** an on-disk chapter directory whose number is not in the
  manifest (`on_disk ⊄ manifest`). Always a violation.
- **Missing-directory direction:** a manifest entry whose number is not on disk
  (`manifest ⊄ on_disk`). Relaxed during drafting only.

## Plan of work

The work proceeds in four atomic, independently committable work items. Each ends
with the validation in "Validation and acceptance". Do not proceed past a failing
gate.

### Work item 1 — ADR 009: phase-gated bijection relaxation

Documentation only; lands first so the code work items can cite it.

Docs to read first: `docs/adr-008-chapter-manifest-mutator.md` (the format and
the §5.4 precedence it established); design §5.2 invariant 5 and §5.4 (the
disk-authoritative model and the §4.3 ordering guarantee the bijection protects);
the roadmap 2.1.7 entry. Skills to load: none beyond en-GB prose discipline
(`en-gb-oxendict`).

Create `docs/adr-009-drafting-bijection-relaxation.md` following the ADR 008
shape (Status, Date, Context and problem statement, Decision drivers, Decision,
Consequences, References). It must state:

- The problem: §5.2 invariant 5 requires exact bijection, but during drafting the
  manifest leads the on-disk directory set, so `check` exits 4 for the whole
  drafting phase (beta finding).
- The decision: while `[phase].current == drafting`, `novel-state check` relaxes
  the bijection to **disk-subset-of-manifest** — the orphan direction and the
  manifest-contiguity check still fire; only the missing-directory direction is
  suppressed. At every other phase, including `final-pass` and `done`, the exact
  bijection is enforced.
- The boundary with reconcile: the relaxation is scoped to the user-facing
  `check` verdict (`check_disk_evidence(..., relax_drafting_bijection=True)`).
  `reconcile` keeps the strict bijection (default flag), so the torn
  `set-chapters` COMPLETE precedence (ADR 008) is unchanged even though that torn
  tree carries `phase=drafting` (cite the existing test). Record this as the
  controlling reason the relaxation is a flag, not an unconditional predicate
  change.
- The §4.3 consequence: the manifest⇄directory ordering guarantee `novel-compile`
  depends on holds again at final-pass before any final compile, so relaxing
  during drafting does not weaken compile ordering (compile runs after the
  bijection re-tightens).
- **The full blast radius (mandatory — enumerate every invariant whose
  enforcement changes, not just the bijection).** State that the relaxation
  changes the enforcement of exactly two disk-evidence invariants during
  drafting: (1) `manifest-disk-bijection` itself, relaxed to disk-subset-of-manifest
  (orphan and contiguity directions still fire); and (2)
  `word-counts-cover-drafts`, which is **not enforced** during a relaxed subset.
  Explain why (2) is a consequence and not a regression: cover-drafts
  (`_disk_word_counts.py` lines 128-130) already defers on any tree where
  `manifest != on_disk`, so it never fired on a subset under the strict detector;
  the relaxation only removes the bijection signal that previously sat in front
  of that deferral. cover-drafts re-enforces once the tree returns to bijection
  and at `final-pass`/`done`. State explicitly that the remaining six disk-evidence
  predicates do not read the manifest⇄disk equality and are unchanged. This
  enumeration is the controlling record so a future reader understands the
  relaxation's true scope (review r1 blocking item 1; pre-mortem prevention).

Append `docs/adr-009-drafting-bijection-relaxation.md` to `docs/contents.md` in
the ADR list (the abstraction-recording rule, AGENTS.md "Abstraction / port /
helper policy").

Tests: none (pure documentation). Validation: `make markdownlint` and
`make nixie` (no Mermaid is added, but the gate is mandatory for markdown
changes).

### Work item 2 — split the bijection verdict and add the phase-gated relaxation

Implements design §5.2 invariant 5's relaxation under ADR 009 / Decision D1, D2,
D3.

Docs to read first: design §5.2 (invariant 5) and §5.4; ADR 009 (work item 1);
the `disk_evidence.py` module docstring (the deliberate-twin and totality
contracts). Skills to load: `leta` (navigate `check_disk_evidence`,
`derive_reconciliation`, and their callers via `leta refs` / `leta show` rather
than ad-hoc grep); `python-router` → `python-types-and-apis` (the keyword-only,
default-valued parameter and the `Phase` identity comparison).

Steps:

1. In `novel_ralph_skill/state/disk_evidence.py`, refactor
   `_check_manifest_disk_bijection(state, working_dir)` so its verdict is computed
   from the two directions explicitly: `orphans = on_disk - manifest` (the orphan
   direction), `missing = manifest - on_disk` (the missing-directory direction),
   and `contiguous = sorted(manifest) == list(range(1, len(manifest) + 1))`. The
   strict verdict fires `MANIFEST_DISK_BIJECTION` when `orphans or missing or not
   contiguous` — byte-for-byte equivalent to today's `manifest == on_disk and
   contiguous`. Keep the existing detail message wording for the strict path so
   no snapshot churns.
2. Give the bijection predicate a widened, keyword-only signature
   `_check_manifest_disk_bijection(state, working_dir, *, relax_drafting:
   bool = False)`. When `relax_drafting and state.phase.current ==
   Phase.DRAFTING`, a verdict whose **only** broken direction is `missing` (i.e.
   `not orphans and contiguous and missing`) returns `None` (coherent). Orphans
   and a non-contiguous manifest still fire in every phase. Import `Phase` from
   `novel_ralph_skill.state.phase`. The predicate already receives `state`, so it
   reads `state.phase.current` directly.
3. **Wiring mechanism (resolves the `_PREDICATES`-uniformity conflict).** The
   `_PREDICATES` loop is a uniform `tuple[Callable[[State, Path], Violation |
   None], ...]` (`disk_evidence.py` lines 264-273), so a per-predicate kwarg
   cannot be threaded through it without widening every predicate. Do **not**
   widen the loop. Instead, **lift the bijection predicate out of the loop** and
   call it explicitly first, then run the remaining seven predicates through the
   loop, concatenating in `DISK_EVIDENCE_INVARIANT_NAMES` order. Concretely:
   - Define `_TAIL_PREDICATES` as the existing tuple **minus**
     `_check_manifest_disk_bijection` (the seven non-bijection predicates, in
     their current order: cursor-plan-present, done-flag-without-draft,
     compiled-matches-drafts, pending-turn-cleared, word-counts-match-drafts,
     log-present, word-counts-cover-drafts).
   - `check_disk_evidence` computes
     `head = _check_manifest_disk_bijection(state, working_dir,
     relax_drafting=relax_drafting_bijection)` first, then
     `tail = (p(state, working_dir) for p in _TAIL_PREDICATES)`, and returns
     `tuple(v for v in (head, *tail) if v is not None)`.
   - Because the bijection is element 0 of `DISK_EVIDENCE_INVARIANT_NAMES`
     (`disk_evidence.py` line 101) and the tail keeps the remaining elements in
     order, the union verdict order is byte-for-byte identical to today's
     single-loop order. Keep `_PREDICATES` defined (or re-derive
     `(_check_manifest_disk_bijection, *_TAIL_PREDICATES)`) so any existing
     reference and the comment at lines 261-263 stay accurate; assert the union
     order in a test (Work item 2 tests). This is the explicit, committed wiring;
     there is no menu.
   - The other seven predicates are unchanged and ignore the flag; only the
     bijection direction changes.
   - If this pushes `disk_evidence.py` over the 400-line cap (it is 300 lines
     today, so the addition fits with margin), extract the bijection predicate
     and `_on_disk_chapter_numbers` into a sibling module
     (`novel_ralph_skill/state/_disk_bijection.py`) re-exported from
     `disk_evidence.py`, mirroring `_disk_word_counts.py` (Constraint: file-size
     cap). Prefer keeping it in place; extract only if the cap is breached.
4. In `novel_ralph_skill/commands/novel_state.py::_disk_evidence_or_state_error`
   (and its `_check` caller), pass `relax_drafting_bijection=True` so the
   user-facing checker relaxes. Update the `_check` docstring to note the
   drafting-phase subset relaxation and cite ADR 009.
5. Leave `derive_reconciliation` (reconcile.py line 345) calling
   `check_disk_evidence(state, working_dir)` with the default — i.e. strict. Add
   a one-line comment there citing D1/ADR 009: reconcile reads the strict
   bijection so the torn `set-chapters` precedence is unaffected.
6. Update the `disk_evidence.py` module docstring to describe the new flag and the
   strict-by-default contract.

Interfaces at end of this work item:

```python
# novel_ralph_skill/state/disk_evidence.py
def check_disk_evidence(
    state: State,
    working_dir: Path,
    *,
    relax_drafting_bijection: bool = False,
) -> tuple[Violation, ...]: ...
```

Tests (add/extend `tests/test_disk_evidence.py`):

- Unit: strict default — `manifest-extra-entry`-shaped tree at `phase=drafting`
  still fires `manifest-disk-bijection` under the default flag (regression guard
  for the corpus agreement suite and reconcile).
- Unit: relaxed flag at `phase=drafting` — the same subset tree returns no
  `manifest-disk-bijection` violation.
- Unit: relaxed flag, orphan directory at `phase=drafting` — an on-disk chapter
  absent from the manifest STILL fires `manifest-disk-bijection` (the
  one-directional guarantee).
- Unit: relaxed flag, non-contiguous manifest at `phase=drafting` — a manifest
  with a gap still fires (contiguity is not relaxed).
- Unit: relaxed flag at `phase=final-pass` and `phase=done` — a manifest entry
  without a directory STILL fires (tightening at the terminal phases).
- Unit (cover-drafts boundary, resolves review r1 blocking item 1): build a
  relaxed drafting subset whose `by_chapter` table key set has DRIFTED (e.g. a
  table key the manifest never declares, or a recount key the table omits) and
  assert the **full relaxed verdict is empty** — i.e. `check_disk_evidence(...,
  relax_drafting_bijection=True)` returns `()`. This pins the documented
  boundary: cover-drafts does NOT fire on a relaxed subset because it already
  defers when `manifest != on_disk`. Add a paired assertion that the SAME tree
  under the **strict** flag fires `manifest-disk-bijection` (and still not
  cover-drafts, proving cover-drafts was already silent), so the test records that
  the relaxation removed only the bijection signal, not a cover-drafts signal
  (D6). A docstring on the test must name D6 and state this is the intended
  boundary, not an accident.
- Unit (union order preserved, resolves review r1 blocking item 3): construct a
  tree that fires several disk-evidence invariants at once (including the
  bijection) under the strict flag and assert the returned invariant-name order
  equals the order they appear in `DISK_EVIDENCE_INVARIANT_NAMES`, proving the
  out-of-loop wiring (bijection first, tail in order) reproduces the old
  single-loop order.
- Unit (reconcile regression): in `tests/test_set_chapters_reconcile.py`, assert
  the existing torn `set-chapters` drafting tree still derives
  `ReconcileAction.COMPLETE_PENDING_TURN` (the strict bijection still fires for
  reconcile). If an equivalent assertion already exists, extend its docstring to
  name D1 rather than duplicating.
- Property (Hypothesis; load the `hypothesis` skill): generate a phase from the
  `Phase` enum and a tree shape from `{exact, subset, orphan, non-contiguous}`,
  build the corresponding `(manifest, on_disk)` sets, and assert the relaxed
  predicate's verdict equals the table:
  `subset` → coherent iff `phase == drafting`; `exact` → always coherent;
  `orphan` → always a violation; `non-contiguous` → always a violation. This pins
  the phase × direction matrix the example tests sample. Keep the strategy
  constructive (no `assume`-heavy filtering, per the `hypothesis` skill's
  filtering-trap guidance).

Validation: `make all` (formatting, lint with 100% docstring coverage, ty
typecheck, pytest, pip-audit). Confirm `tests/test_novel_state_check_disk.py`
and the reconcile suite stay green (strict default preserved).

### Work item 3 — corpus oracle twin + positive relaxed case

Keeps the independent corpus oracle in lock-step with the relaxed production path
and proves the relaxation through the corpus loop, satisfying the deliberate-twin
discipline (developers' guide "Invariant validation").

Docs to read first: developers' guide "Invariant validation" (the twin policy and
the agreement suite); `tests/working_corpus/_oracle_disk.py` and `_variants.py`
(the oracle twin and the variant registry); design §5.2 invariant 5. Skills:
`leta` (navigate the oracle twins and the variant registry); `python-testing`
(corpus fixtures and parametrization).

Steps:

1. Mirror the production split in the oracle twin
   `tests/working_corpus/_oracle_disk.py::_check_manifest_disk_bijection`: add an
   optional `relax_drafting_bijection`-style path (reading the materialised
   `state.toml` `[phase].current`) that relaxes the missing-directory direction
   during drafting, exactly mirroring the production predicate. The **strict** twin
   path remains the default the agreement suite calls, so
   `test_union_detector_agrees_with_corpus_oracle` is unchanged.
2. Add a relaxed agreement assertion: a focused test that, for the drafting subset
   tree and for the `final-pass`/`done` exact-bijection trees, the **relaxed**
   production `check_disk_evidence(..., relax_drafting_bijection=True)` agrees with
   the **relaxed** oracle twin. This is the relaxed analogue of the strict
   agreement suite, scoped to the bijection name so it stays small.
3. Add a positive (coherent) drafting-subset corpus fixture and assert the
   **full relaxed verdict tuple is empty** — not merely that the bijection name
   is absent (resolves review r1 blocking item 2). A coherent subset must pass
   every other disk-evidence predicate, so the fixture must be constructed so that
   each is satisfied:
   - **Exact fixture.** Start from `COHERENT_BASELINE` / `_BASE`
     (`PHASE_STATES["drafting"]`, three drafted chapters `{1,2,3}` all with
     matching `draft_words`, `current_chapter=3`). Produce a subset by marking the
     last manifest chapter as **present in the manifest but absent on disk**: it
     must appear in `[chapters]` yet have no `manuscript/chapter-03/` directory.
     The cleanest mechanism is a new `WorkingTreeSpec` field or helper in
     `tests/working_corpus/_library.py` (e.g. `manifest_present_disk_absent`) that
     keeps chapter 3 in the manifest array (so `manifest = {1,2,3}`) but omits its
     directory and `draft.md` (so `on_disk = {1,2}`). `manifest_only_numbers`
     alone adds a manifest entry with no `ChapterSpec`; here we instead need an
     existing drafted `ChapterSpec` whose directory the builder skips — confirm
     the builder path in `tests/working_corpus/_builder.py` (the `_chapters_array`
     manifest writer at lines 106-133 versus the directory/`draft.md` writer) and
     add the minimal field that decouples "in manifest" from "on disk" for a real
     chapter. If the existing `in_manifest` / directory-writing split cannot
     express this without a new field, add the field; do not force it through
     `manifest_only_numbers` (which produces a *placeholder* chapter, not a real
     drafted one absent from disk).
   - **Satisfy the remaining predicates by construction:**
     - `cursor-plan-present`: set `current_chapter` to a chapter that IS on disk
       (e.g. 1 or 2) with `current_scene == 0` and `current_beat == 0`, OR keep
       the cursor on a present chapter whose `scenes.md`/`beats.md` exist, so the
       predicate's `0 < current_chapter <= len(chapters)` guard plus zeroed
       scene/beat cursor never demands an absent plan.
     - `done-flag-without-draft`: ensure no `done.flag` is written for the absent
       chapter (it has no directory, so none is written) and present chapters keep
       non-empty drafts.
     - `word-counts-match-drafts`: the `by_chapter` table values for the PRESENT
       chapters must equal their on-disk token counts (the baseline already does
       this via `derive_by_chapter`); the absent chapter's table entry is a
       non-shared key and is ignored (lines 92-96).
     - `compiled-matches-drafts`, `pending-turn-cleared`, `log-present`: the
       drafting baseline already satisfies these (no `compiled.md`, no
       `pending_turn`, `log.md` present).
     - `word-counts-cover-drafts`: defers because `manifest != on_disk` (D6) — it
       contributes nothing, which is the documented boundary.
   - **Assertion.** Assert
     `check_disk_evidence(state, working_dir, relax_drafting_bijection=True) ==
     ()` (the full relaxed verdict is empty), and separately that
     `check_disk_evidence(state, working_dir)` (strict default) fires exactly
     `manifest-disk-bijection` and nothing else. This proves the relaxation yields
     a genuinely clean exit-0 tree under the relaxed checker and is exactly the
     phase-gated flag and nothing more.

Tests: the relaxed agreement test and the positive drafting-subset case above.
Run alongside the existing strict agreement suite to prove no strict regression.

Validation: `make all`. Confirm both the strict and relaxed agreement tests pass
and the strict corpus suite is unchanged.

### Work item 4 — e2e proof and documentation

Proves the externally observable workflow change and updates the guides
(AGENTS.md "Add end-to-end tests where a change affects … command-line
behaviour"; the change alters `novel-state check`'s exit code mid-draft).

Docs to read first: `tests/test_console_scripts_e2e.py` (the cuprum
absolute-path catalogue harness); `docs/users-guide.md` lines 144-178 (the
disk-evidence names and the disk-aware `check` description);
`docs/developers-guide.md` "Invariant validation" (the §5.2 table and the
disk-evidence list). Skills: `leta`; `en-gb-oxendict`; the `firecrawl` skill is
**not** required here — no new external-library behaviour is leaned on (cuprum
0.1.0's absolute-path allowlisting is already verified against
`/data/leynos/Projects/cuprum/cuprum/catalogue.py` and exercised by the existing
e2e test; Decision D5).

Steps:

1. Add an e2e scenario (extend the existing console-scripts e2e module or a new
   `tests/test_drafting_bijection_e2e.py`) that builds a real `working/` tree with
   a drafting-phase `state.toml` declaring chapters 1..3 and only `chapter-01/`
   on disk, runs the installed `novel-state check` console-script **by absolute
   path** through a cuprum `ProgramCatalogue`, and asserts exit 0.
   - **Exact invocation (resolves review r1 advisory).** `novel-state` is a
     command-group app: a bare invocation prints help and exits 0, so the
     subcommand argument `"check"` MUST be passed. Use the proven pattern from
     `tests/test_console_scripts_e2e.py` lines 113-119, which appends the extra
     argv: `prog = Program(str(script_path))`,
     `catalogue = single_program_catalogue("novel-ralph-e2e-scripts", prog)`,
     then `sh.make(prog, catalogue=catalogue)("check").run_sync(...)` with
     `context=ExecutionContext(cwd=run_cwd)` and `capture=True`.
     The `(...)("check")` builder call supplies the subcommand argv
     (`_REAL_PATH_ARGV["novel-state"] == ("check",)`, line 44); omitting it prints
     help and never reaches exit 0/4. The `single_program_catalogue` fixture is
     `tests/conftest.py` line 246.
   - A companion case advances the same tree to `final-pass` (all manifest
     entries, one missing directory) and asserts exit 4 with
     `manifest-disk-bijection` in the JSON `result.violations`.
   - **Timeout/slow marks (cite precedent; do not invent).** Mark both cases
     `@pytest.mark.slow` and `@pytest.mark.timeout(180)`, reusing the exact value
     and pattern proven at `tests/test_console_scripts_e2e.py` lines 127-128. The
     repo configures a global `timeout = 30` (`pyproject.toml` line 326); the
     per-test `@pytest.mark.timeout(180)` override composes with the xdist run the
     Makefile uses, which is the locally-proven precedent (that existing e2e test
     builds and installs the wheel under xdist with the 180s override). Do not
     invent a new timeout value.
   - **Reconciliation payload on the relaxed-clean tree (resolves review r1
     advisory).** Assert that the exit-0 drafting-subset case carries NO
     `reconciliation` key in its JSON `result`: `_check` attaches reconciliation
     only when `disk_evidence` fired (`novel_state.py` lines 243-246), and a
     relaxed-clean subset yields an empty disk-evidence verdict, so no
     reconciliation is derived. This is the correct outcome — a clean tree
     implies no repair — and the test records it so the acceptance criteria
     account for the payload's absence.
2. Update `docs/users-guide.md` `manifest-disk-bijection` bullet (line 171) to
   note that during drafting `check` accepts a tree whose on-disk chapters are a
   subset of the manifest (an orphan directory or a manifest gap still flags, and
   the exact bijection returns at `final-pass`/`done`). Add a short worked example
   under the disk-aware `check` section.
3. Update `docs/developers-guide.md` "Invariant validation": annotate the §5.2
   invariant-5 row and the disk-evidence `manifest-disk-bijection` entry with the
   drafting-phase relaxation, the `relax_drafting_bijection` flag, and the
   strict/relaxed split between `check` and `reconcile`; cite ADR 009. Also note,
   against the `word-counts-cover-drafts` entry, that it is not enforced during
   a relaxed drafting subset (it defers on `manifest != on_disk`) and re-enforces
   at bijection and at final-pass/done (D6), so the guide's invariant table records
   the full relaxation blast radius, not just the bijection.

Tests: the e2e cases above. Validation: `make all`, then `make markdownlint` and
`make nixie` for the two guide changes.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-7`.

Per work item, after the edits:

```bash
make all
```

Expect: `check-fmt`, `lint` (Ruff + 100% interrogate docstring coverage +
Pylint), `typecheck` (`ty check`), `test` (pytest under xdist), and `audit`
(`pip-audit`) all pass. For the markdown-touching work items (1 and 4) also run:

```bash
make markdownlint
make nixie
```

Expect both to pass (no Mermaid is added; `nixie` is a no-op-clean gate for the
ADR and guide edits).

To see the new behaviour by hand after work item 2:

```bash
# Build a drafting tree whose manifest is 1..3 but only chapter-01 exists,
# then run check; expect exit 0 (was exit 4 before this change).
```

Replace the placeholder with the project's standard tree-construction fixture
(`tests/working_corpus`); the e2e test in work item 4 encodes the canonical
transcript.

## Validation and acceptance

Quality criteria (what "done" means):

- **Tests:** `make test` passes. New tests fail before the work-item-2 edit and
  pass after:
  - `tests/test_disk_evidence.py` relaxed-flag cases (subset coherent at
    drafting; orphan and non-contiguous still fire; subset fires at
    final-pass/done).
  - the Hypothesis phase × direction property.
  - the relaxed corpus agreement test and positive drafting-subset case
    (work item 3) — the latter asserts the FULL relaxed verdict is `()`.
  - the cover-drafts boundary test (D6): a drifted-`by_chapter` relaxed subset
    still yields an empty relaxed verdict; the union-order test confirming the
    out-of-loop wiring preserves `DISK_EVIDENCE_INVARIANT_NAMES` order.
  - the e2e exit-0-mid-draft / exit-4-at-final-pass cases (work item 4), the
    exit-0 case also asserting no `reconciliation` key in `result`.
  - the reconcile regression assertion (torn `set-chapters` drafting tree still
    COMPLETEs) stays green throughout.
- **Strict invariants preserved:** `tests/test_novel_state_check_disk.py`
  strict agreement suite and the reconcile suite pass **unchanged**.
- **Lint/typecheck:** `make lint` and `make typecheck` pass; 100% docstring
  coverage holds (interrogate); no new lint suppression without a linked fix.
- **Markdown:** `make markdownlint` and `make nixie` pass for the ADR and the two
  guide edits.

Quality method (how we check): run `make all` (then `make markdownlint` and
`make nixie` for markdown work items) at the end of each work item; do not commit
a work item whose gates fail (AGENTS.md "Change quality and committing").

Acceptance, phrased as behaviour:

- A drafting-phase tree with manifest `{1,2,3}` and on-disk `{1}` → `novel-state
  check` exits 0 (was 4).
- The same tree with an extra on-disk `chapter-09/` not in the manifest →
  `novel-state check` exits 4 with `manifest-disk-bijection`.
- A drafting-phase tree with a manifest gap (`{1,3}`) → exits 4 with
  `manifest-disk-bijection`.
- The `{1,2,3}` manifest / `{1}` on-disk tree advanced to `final-pass` → exits 4
  with `manifest-disk-bijection`.
- A torn `set-chapters` reconcile tree at `phase=drafting` → still derives
  `complete-pending-turn` (reconcile unchanged).
- A drafting-phase tree with manifest `{1,2,3}`, on-disk `{1}`, AND a drifted
  `by_chapter` table → `novel-state check` still exits 0 (cover-drafts is the
  documented un-enforced boundary during a relaxed subset, D6); the same drift is
  caught once the tree returns to bijection or reaches final-pass.
- The exit-0 drafting-subset tree's `result` JSON carries no `reconciliation`
  key (an empty disk-evidence verdict attaches no reconciliation payload).

## Idempotence and recovery

Every step is a code or doc edit re-runnable without drift; `make all` is
idempotent. No data migration, no destructive operation. If a work item's gate
fails, revert the work item's edits (it is a single atomic commit) and retry;
nothing persists outside the worktree.

## Artifacts and notes

Key verified facts pinned for the implementer:

- cuprum 0.1.0 (locked, `uv.lock` line 113) allowlists any `Program` string
  including an absolute path; the existing e2e harness
  (`tests/test_console_scripts_e2e.py` lines 105-119) is the only cuprum surface
  this task uses. Verified against `/data/leynos/Projects/cuprum/cuprum/
  catalogue.py` (`ProgramCatalogue`) and the test's own docstring.
- `_check_manifest_disk_bijection` today: `manifest == on_disk and contiguous`
  (`disk_evidence.py` lines 122-126). The split into orphan/missing/contiguity is
  behaviour-preserving for the strict path.
- `derive_reconciliation` reads `check_disk_evidence(...)` (reconcile.py line 345)
  and needs the strict bijection (torn `set-chapters` test at
  `tests/test_set_chapters_reconcile.py` line 125 uses `phase_current="drafting"`).
- `COHERENT_BASELINE` (`_BASE`) is the drafting baseline
  (`tests/working_corpus/_library.py` line 118), so `manifest-extra-entry` is
  already a drafting-phase tree.
- `_check_word_counts_cover_drafts` defers (`return None`) on
  `manifest != _on_disk_chapter_numbers(working_dir)`
  (`novel_ralph_skill/state/_disk_word_counts.py` lines 128-130), so it never
  fires on a subset tree and is the second invariant whose enforcement the
  relaxation changes (D6). `_check_word_counts_match_drafts` compares only shared
  keys (same file, lines 92-96), so it stays clean on a subset.
- The `_PREDICATES` loop is uniform `tuple[Callable[[State, Path], Violation |
  None], ...]` (`disk_evidence.py` lines 264-273); the chosen wiring lifts
  `_check_manifest_disk_bijection` out of the loop and calls it first with the
  flag, then runs the seven tail predicates, preserving
  `DISK_EVIDENCE_INVARIANT_NAMES` order (bijection is element 0, line 101).
- e2e invocation must pass the `"check"` subcommand:
  `sh.make(prog, catalogue=catalogue)("check").run_sync(...)`
  (`tests/test_console_scripts_e2e.py` line 44 `_REAL_PATH_ARGV`, lines 113-119);
  reuse `@pytest.mark.timeout(180)` + `@pytest.mark.slow`
  (lines 127-128) over the global `timeout = 30` (`pyproject.toml` line 326).

## Revision note (round 2)

Revised in response to the round-1 Logisphere design review
(`docs/execplans/roadmap-2-1-7.review-r1.md`), which returned REVISE.

What changed:

- **Blocking item 1 (cover-drafts coupling).** Added Decision D6 analysing the
  relaxation's true blast radius: relaxing the missing-directory direction also
  leaves `word-counts-cover-drafts` un-enforced during a relaxed subset, because
  that predicate already defers on `manifest != on_disk` and so never fired on a
  subset under the strict detector. Added the analysis to "Context and
  orientation", a Risk entry, a cross-reference from D2, an enumeration
  requirement to the ADR (Work item 1), and a cover-drafts boundary test to Work
  item 2 (a drifted-`by_chapter` relaxed subset still yields an empty relaxed
  verdict, with the same tree firing only `manifest-disk-bijection` under strict).
- **Blocking item 2 (positive fixture must prove full cleanliness).** Rewrote
  Work item 3 step 3 to specify the exact coherent drafting-subset fixture (a real
  drafted chapter present in the manifest but absent on disk, with cursor on a
  present chapter and present-chapter table values matching disk) and to assert
  the FULL relaxed verdict is `()`, not merely the absence of the bijection name;
  paired with a strict-default assertion that the same tree fires only
  `manifest-disk-bijection`.
- **Blocking item 3 (flag-threading mechanism).** Committed to one explicit
  wiring in Work item 2 step 3: lift `_check_manifest_disk_bijection` out of the
  uniform `_PREDICATES` loop, call it first with the keyword-only flag, run the
  seven tail predicates through the loop, and concatenate in
  `DISK_EVIDENCE_INVARIANT_NAMES` order. Added a union-order test pinning that the
  out-of-loop assembly reproduces the old single-loop order.
- **Advisories.** Fixed the e2e recipe to pass the `"check"` subcommand argv via
  the `(...)("check")` builder call; cited the `@pytest.mark.timeout(180)` /
  global-`timeout = 30` precedent and reused 180s; added an acceptance assertion
  and Work item 4 step that the relaxed-clean tree carries no `reconciliation`
  key. Recorded Decision D7 explaining why the flag beat the command-layer-drop
  alternative (the `Violation` detail is free text, so the command cannot
  distinguish missing-direction-only breaks without re-deriving direction).

How it affects remaining work: the spine (D1/D2/D3) is unchanged; the revisions
tighten the wiring to one concrete mechanism, widen the documentation and test
obligations to cover the full blast radius, and make the positive fixture prove
exit-0 cleanliness rather than assert it.

## Interfaces and dependencies

No new dependency. The single sanctioned public-signature change:

```python
# novel_ralph_skill/state/disk_evidence.py
def check_disk_evidence(
    state: State,
    working_dir: Path,
    *,
    relax_drafting_bijection: bool = False,
) -> tuple[Violation, ...]: ...
```

`_check()` (`novel_ralph_skill/commands/novel_state.py`) calls it with
`relax_drafting_bijection=True`; `derive_reconciliation`
(`novel_ralph_skill/state/reconcile.py`) calls it with the default (strict). The
invariant name `manifest-disk-bijection`
(`disk_evidence.MANIFEST_DISK_BIJECTION`) is unchanged. The oracle twin
`tests/working_corpus/_oracle_disk.py::_check_manifest_disk_bijection` mirrors the
production split and relaxation.
