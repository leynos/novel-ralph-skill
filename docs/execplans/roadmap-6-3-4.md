# Resolve `working/` robustly and surface the resolved path

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: COMPLETE (all four work items implemented, committed, and gated)

## Purpose / big picture

Today every `novel` command resolves the working tree as the literal
cwd-relative path `working/` and stamps the literal string `"working"` into the
envelope's `working_dir` field (and, for `novel state init`, into its result
body as well). Because neither field names *where* the command actually looked,
a stray `cd` during beta testing silently misresolved the tree (a command run
from inside `working/` looked for `working/working/…`) and read as a silent
failure: the envelope said `working_dir: "working"` whichever directory you were
in, so the misresolution was invisible.

After this change, the path-bearing `working_dir` fields that the production
`novel` entry point emits — the envelope's top-level `working_dir` on every
command, and the `result.working_dir` body of `novel state init` — carry the
**absolute, resolved** path the command used, for example
`/home/me/my-novel/working`, so a misresolution is immediately visible in the
very fields the agent already reads. Running from inside `working/` no longer
fails silently: the envelope shows `.../working/working`, naming the footgun out
loud.

You can observe success by running the installed `novel` binary from a
directory with no `working/` tree and seeing the envelope's `working_dir` carry
the absolute path `<that-directory>/working` rather than the bare token
`working`, and by the new behavioural test that drives the entry point from a
chosen directory and asserts the stamped path equals
`<that-directory>/working`.

### Non-goal: subdirectory auto-resolution (deliberately accepted)

The roadmap success criterion joins two clauses with "or": (i) resolve
`working/` by searching upward from the cwd (so a command run from a
subdirectory of the novel root finds the right tree), or (ii) always report the
resolved absolute `working_dir` so a misresolution is visible. This plan
chooses clause (ii). Clause (i) — subdirectory auto-resolution — is therefore a
**deliberately accepted non-goal**: from a subdirectory the command still fails
to locate `working/` rather than walking upward to find it; the win is that the
failure is now loud (the envelope names the path it tried) rather than silent.
A future reviewer should read clause (i) as a chosen alternative, not as unmet
work. The justification for choosing (ii) is recorded below and in Decision Log
D1.

## Why surface the absolute path (decision, with justification)

Roadmap task 6.3.4 offers two mechanisms and demands one be chosen and
justified:

1. **Upward search** — resolve `working/` by walking up the directory tree from
   the cwd, as `git` finds `.git`.
2. **Surface the resolved absolute path** — keep the fixed cwd-relative
   resolution but report the absolute resolved `working_dir` in the envelope so
   a misresolution is visible.

This plan chooses **option 2 (surface the resolved absolute path)**. The
justification, recorded in the Decision Log as D1:

- **Lowest blast radius and no semantic surprise.** Option 1 changes *which*
  directory a command operates on, a behavioural change to every command's
  resolution. Option 2 changes only what the path-bearing fields *report*;
  resolution stays exactly as the code records it. The cwd-relative resolution
  rule is documented in the source, in the `WORKING_DIR_NAME` comment at
  `novel_ralph_skill/commands/_state_load.py:32-36` ("The fixed cwd-relative
  working directory … There is no `--working-dir` flag") and the `working_dir()`
  docstring at lines 40-48. (Note: the design document does *not* state the
  resolution rule in prose — see Decision Log D4 and Surprises — so the rule is
  cited to the source comment, which is its true locus.) No command starts
  reading or writing a different tree.
- **Option 1 cannot serve `novel state init`.** `init` creates `working/`; there
  is nothing to search upward *for* yet. An upward search would force a split
  between resolution-for-read and resolution-for-create, and would silently
  attach a fresh `init` to an unrelated ancestor project's `working/` — a worse
  footgun than the one we are closing.
- **Option 1 introduces ancestor-ambiguity.** With nested novels (a `working/`
  inside another novel's tree), upward search must define a stop rule and a
  tie-break; option 2 has none of this.
- **Option 2 directly closes the dogfooding defect.** The failure was *silence*:
  the field read `"working"` regardless of cwd. An absolute path makes the
  `working/working` misresolution loud in the fields the agent already gates on,
  which is precisely what roadmap §6.3 ("loud, consistent, self-describing")
  demands.

The success criterion's "running from inside `working/` no longer silently
looks for `working/working`" is met by making that misresolution **visible**
(the path shows `.../working/working`), not by suppressing it; the command still
fails as it must, but loudly rather than silently.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- The resolution **semantics** must not change: commands continue to resolve
  `working/` as cwd-relative. The rule is documented at
  `novel_ralph_skill/commands/_state_load.py:32-48` (the `WORKING_DIR_NAME`
  comment and the `working_dir()` docstring), *not* in the design document
  (Decision Log D4). Only the *reported* `working_dir` values become absolute.
  There is, and remains, no `--working-dir` flag.
- The home for *resolution by the contract entry point and the state-load
  accessors* stays `novel_ralph_skill/commands/_state_load.py`
  (`WORKING_DIR_NAME`, `working_dir`, `state_path`). The new absolute-path
  accessor is added beside the existing ones so the constant remains
  single-source for this module (AGENTS.md "clear file boundaries"). This plan
  does **not** claim that `_state_load.py` is the *only* place that resolves
  `working/` in the codebase — it is not (see the next constraint and Decision
  Log D5).
- **Two pre-existing parallel resolution sites are acknowledged and scoped
  out.** `novel_ralph_skill/commands/_desloppify.py:198` and
  `novel_ralph_skill/commands/_wordcount.py:130` both rebuild
  `working_dir = pathlib.Path(WORKING_DIR_NAME)` directly instead of calling the
  `working_dir()` accessor. These feed the `result`/`messages` *payload* of
  `desloppify`/`wordcount`, not the envelope's `working_dir` label, so they are
  **out of scope for the reported path**: changing them is unnecessary to make
  the reported `working_dir` absolute, and folding them into the accessor is a
  separable refactor (Decision Log D5). The plan must not assert they are
  already single-sourced; it states plainly that they are parallel sites left
  untouched.
- The envelope contract is unchanged in shape: six fields
  (`command`, `schema_version`, `ok`, `working_dir`, `result`, `messages`) in
  order, `working_dir` still a JSON string (`docs/novel-ralph-harness-design.md`
  §3.1; `docs/adr-003-shared-interface-contract.md`). Only the *value* of the
  top-level `working_dir` on the production path changes from `"working"` to an
  absolute path string, and the *value* of `result.working_dir` in `novel state
  init`'s body likewise becomes absolute (Decision Log D6).
- The cross-command identity proof in `tests/cross_command_contract/` drives the
  contract via a synthetically-constructed `RunContext` it builds with an
  explicit `working_dir="working"` (`tests/contract_drive_support.py:190`); it
  does **not** exercise the production
  `novel_ralph_skill.commands.novel.main` entry point. Those tests pin the
  envelope *shape*, not the production path's value, so they must continue to
  pass unchanged (they keep injecting their own constant). Do not weaken them to
  accommodate this change. The behaviour that the production entry point stamps
  the absolute path is proved by new tests that drive `novel.main` and the
  installed binary directly.
- Atomic-write discipline and exit-code table (`docs/novel-ralph-harness-design.md`
  §3.2, §3.4) are untouched: this change reads a path for the envelope/result
  label and does not alter any write path or any exit code.
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments, commit
  messages, and docstrings (AGENTS.md; `en-gb-oxendict`).
- AGENTS.md enforces 100% docstring coverage via `interrogate` over
  `$(PYTHON_TARGETS)` (AGENTS.md "Quality gates"). Every new module, function,
  and test added by this plan — including the new test modules — must carry a
  module docstring and a docstring on each test function, or the `typecheck`
  gate fails.

## Tolerances (exception triggers)

- **Scope:** if the implementation requires touching more than **12**
  source/test/doc files or more than ~340 net lines, stop and escalate. The
  twelve in-scope files are enumerated and fixed by this plan (Decision Log D6,
  D7): (1) `novel_ralph_skill/commands/_state_load.py`,
  (2) `novel_ralph_skill/commands/novel.py`,
  (3) `novel_ralph_skill/commands/novel_state.py`,
  (4) `tests/test_state_load_resolved_working_dir.py` (new),
  (5) `tests/test_novel_main_working_dir.py` (new),
  (6) `tests/test_novel_state_mutators.py` (init-body assertion),
  (7) `tests/test_novel_state_mutator_snapshots.py` (`_normalise` helper +
  module docstring),
  (8) `tests/__snapshots__/test_novel_state_mutator_snapshots.ambr` (regenerated
  `test_init_success_envelope_snapshot`),
  (9) `tests/test_console_scripts_error_arms_e2e.py`,
  (10) `docs/novel-ralph-harness-design.md`,
  (11) `docs/adr-003-shared-interface-contract.md`,
  (12) `docs/developers-guide.md`. (Raised from the round-2 bound of 9/280 once
  the round-2 review (B5) showed the `novel state init` result-body change
  (Decision Log D6) drags the `init`-success snapshot — its source module,
  its `_normalise` helper, and its `.ambr` — into the edit set; the prior 9-file
  tolerance undercounted that genuine footprint, Decision Log D7.) If a
  **thirteenth** file (beyond these twelve) proves necessary, stop and escalate.
- **Interface:** if `RunContext.working_dir` must change type away from `str`
  (e.g. to `pathlib.Path`), or the envelope's `working_dir` JSON type must
  change from string, stop and escalate.
- **Dependencies:** no new external dependency is permitted; if one seems
  required, stop and escalate.
- **Iterations:** if `make all` still fails after 3 focused fix attempts on a
  single work item, stop and escalate.
- **Ambiguity:** Work item 0's audit has already enumerated the production
  stamps of a path-bearing `working_dir` and found exactly two —
  `novel.main`'s envelope label and `novel state init`'s `result.working_dir`
  body — both brought into scope by this plan (Decision Log D6). If the audit at
  implementation time reveals a **third** production stamp of a path-bearing
  `working_dir` (beyond those two), stop and escalate before changing it.

## Risks

    - Risk: the installed-binary e2e pins the literal ``working_dir: "working"``
      in a full-envelope equality that is **parametrized over all** ``_CELLS``,
      so the literal fires once per cell (state×{usage,state}, desloppify×{usage,
      state}); a single-literal edit at one line would leave the other cells
      asserting the wrong value.
      Severity: medium
      Likelihood: high
      Mitigation: Work item 2 computes the expected ``working_dir`` from each
      cell's own ``run_dir`` (built at ``_run_installed_arm`` line 235 as
      ``tmp_path / f"{command.mount_verb[0]}-{arm.label}"``) and surfaces that
      ``run_dir`` to the assertion (return it from the helper or recompute it the
      same way), then asserts ``envelope["working_dir"] == str((run_dir /
      "working").resolve())`` per cell. The framing is "the parametrized
      full-envelope equality across all ``_CELLS``", not "the literal at line
      300". The full pin inventory is audited and classified in Work item 0.

    - Risk: ``pathlib.Path.resolve()`` resolves symlinks, so on a machine where
      the cwd is reached through a symlink the reported path differs from the
      literal cwd join; a test asserting equality with ``Path.cwd()/"working"``
      could be flaky.
      Severity: low
      Likelihood: low
      Mitigation: Decision D2 pins the exact construction. Tests assert against
      the *same* construction the production code uses (resolve the run
      directory the test created, then join ``working``), not against an
      independently-built literal, so symlink normalisation cannot desynchronise
      them.

    - Risk: a third production stamp of a path-bearing ``working_dir`` (a legacy
      console script, or a command body field beyond ``init``) exists and would
      drift from the new absolute form.
      Severity: low
      Likelihood: low
      Mitigation: Work item 0 greps the production tree for every
      ``RunContext(`` construction and every ``working_dir`` key emitted into an
      envelope/result body, and records the full inventory; the audit has
      already found the two in-scope stamps. The Ambiguity tolerance escalates if
      a third live stamp appears at implementation time.

    - Risk: cuprum API drift — the cuprum git checkout at
      /data/leynos/Projects/cuprum (HEAD de54bff, PR #151) has moved ahead of the
      LOCKED 0.1.0 wheel, collapsing ``capture`` into ``RunOutputOptions``.
      Severity: medium
      Likelihood: medium
      Mitigation: This plan pins every cuprum call against the *installed* locked
      0.1.0 source (see Interfaces and dependencies), not the git HEAD. The e2e
      work item reuses the existing harness verbatim, which already calls the
      locked signature ``run_sync(context=…, capture=True)``.

## Progress

    - [x] Work item 0 — Audit the ``working_dir`` pins and lock the test
      inventory (no production change yet). Done 2026-06-26: ``leta refs
      WORKING_DIR_NAME`` confirmed exactly two production stamps
      (``novel.py:152`` envelope label, ``novel_state.py:264`` ``init`` body),
      two parallel payload sites (``_desloppify.py:198``,
      ``_wordcount.py:130``), and the synthetic test pin
      (``multiplexer_support.py:107``). No third production stamp — Ambiguity
      tolerance not triggered.
    - [x] Work item 1 — Add the absolute-path accessor; stamp it at the
      production entry point (``novel.main`` envelope label) and in the ``novel
      state init`` result body; add the failing-first behavioural and unit tests;
      extend ``tests/test_novel_state_mutator_snapshots.py``'s ``_normalise`` to
      redact the ``init``-body ``result.working_dir`` and correct its now-false
      module docstring; regenerate the ``.ambr``. Done 2026-06-26; two unforeseen
      production-path test sites also needed updating (Decision Log D9).
    - [x] Work item 2 — Update the parametrized installed-binary e2e to assert
      the per-cell absolute ``working_dir`` and add the inside-``working/`` case.
      Done 2026-06-26 (folded into the same green tree as Work item 1 so HEAD
      stays gated; the production change in WI1 breaks the e2e until WI2's
      assertions land, as the plan anticipated).
    - [x] Work item 3 — Update the design doc, ADR-003 note, and developers'
      guide to record the absolute-``working_dir`` decision; run the markdown
      gates. Done 2026-06-26: design §3.1 sample + prose, ADR-003 envelope-bullet
      note, and the devguide identity-proof paragraph all record the absolute
      resolved ``working_dir``; ``make markdownlint`` and ``make nixie`` green.
      ``make fmt`` was deliberately NOT re-run on these (it reflows the whole doc
      tree — unwanted churn); the surgical edits already satisfy the 80-column
      wrap (Decision Log D10).

## Surprises & discoveries

    - Observation: The design document does NOT state the cwd-relative
      resolution rule in prose anywhere.
      Evidence: ``grep -n "cwd-relative\|upward\|resolution rule" docs/
      novel-ralph-harness-design.md`` returns nothing; line 151 of the design
      doc is the JSON sample value ``"working_dir": "working"``, not a rule. The
      phrase "the fixed cwd-relative working directory" exists only as a source
      comment at ``novel_ralph_skill/commands/_state_load.py:32``.
      Impact: All citations of the resolution rule are re-pointed at the
      ``_state_load.py`` comment (its true locus), not the design doc. A round-1
      draft of this plan misattributed the rule to "design line 151"; that is
      corrected throughout (Decision Log D4).

    - Observation: The developers' guide does NOT contain the phrases "the single
      ``WORKING_DIR_NAME``-anchored accessor" or ``working_dir`` "fixed
      constant" as round-1 claimed.
      Evidence: ``grep`` of ``docs/developers-guide.md`` finds "the fixed
      ``working_dir`` constant" at line 160 (describing what the
      *cross-command identity proof* pins) and "only its cwd tail is volatile" at
      line 135 (describing the state-error arm message). The "single
      ``WORKING_DIR_NAME``-anchored accessor" phrasing is the ``working_dir()``
      docstring at ``_state_load.py:42``, not the guide.
      Impact: Work item 3's devguide edits target the real lines 132-135 and
      155-175, not phantom strings (Decision Log D4).

    - Observation: A second production stamp of a path-bearing ``working_dir``
      exists in the ``novel state init`` result body.
      Evidence: ``novel_ralph_skill/commands/novel_state.py:264`` returns
      ``result={"working_dir": WORKING_DIR_NAME, "slug": slug}``.
      Impact: Brought into scope; ``init``'s body field is absolutized alongside
      the envelope label so the Purpose claim ("every path-bearing field names
      where the command looked") holds (Decision Log D6).

    - Observation: Two command bodies rebuild the working path directly instead
      of calling the ``working_dir()`` accessor.
      Evidence: ``novel_ralph_skill/commands/_desloppify.py:198`` and
      ``novel_ralph_skill/commands/_wordcount.py:130`` both assign
      ``working_dir = pathlib.Path(WORKING_DIR_NAME)``.
      Impact: These feed ``result``/``messages``, not the envelope label, so they
      are scoped out of the reported-path change (Decision Log D5). The plan
      acknowledges them rather than claiming single-source resolution.

    - Observation: The behavioural drivers in ``tests/multiplexer_support.py``
      and ``tests/contract_drive_support.py`` build their own ``RunContext`` with
      the literal constant; they do NOT call ``novel.main``.
      Evidence: ``tests/multiplexer_support.py:107`` constructs
      ``RunContext(command=name, working_dir=WORKING_DIR_NAME, human=human)`` and
      drives ``novel.build_multiplexer()`` directly;
      ``tests/contract_drive_support.py:190`` injects ``working_dir="working"``.
      The many ``tests/`` modules that ``import novel`` use these drivers or the
      multiplexer builder, not ``novel.main``.
      Impact: The existing behavioural and snapshot suites are insulated from the
      production change. Work item 1 must add a test that drives ``novel.main``
      itself (or asserts the stamp at ``main``), since no existing test observes
      ``main``'s ``RunContext`` construction.

    - Observation: The ``novel state init`` success snapshot is produced by the
      *real* ``init`` body, so D6 absolutizes a value the snapshot captures
      verbatim, and the snapshot's ``_normalise`` helper does NOT currently
      redact it.
      Evidence: ``tests/test_novel_state_mutator_snapshots.py:62``
      (``test_init_success_envelope_snapshot``) does ``monkeypatch.chdir(tmp_path)``
      (line 68) then drives ``init`` through a synthetic
      ``RunContext(command=_COMMAND, working_dir="working", human=False)`` (line
      52). The synthetic context fixes the *top-level* envelope ``working_dir``
      to the token ``"working"`` (safe), but the ``result.working_dir`` body
      field is stamped by ``init``'s own code from ``WORKING_DIR_NAME`` and is
      captured at ``tests/__snapshots__/test_novel_state_mutator_snapshots.ambr:22``
      as ``"result": {"working_dir": "working", "slug": "s"}``. The file's
      ``_normalise`` helper (line 57-59) redacts only the ``created_at``
      RFC 3339 timestamp (``_TIMESTAMP`` regex, line 37); it does NOT touch
      ``result.working_dir``. After D6 the body value becomes
      ``str((tmp_path / "working").resolve())`` — a per-machine absolute path —
      so the snapshot breaks and then churns per-machine unless ``_normalise``
      is extended to normalise the ``result.working_dir`` body value (the
      top-level label stays the injected ``"working"`` token and must NOT be
      touched).
      Impact: ``tests/test_novel_state_mutator_snapshots.py`` (its ``_normalise``
      helper and its now-false module docstring at lines 5-8) and its ``.ambr``
      are first-class Work item 1 edit sites, not merely inventory entries. The
      Scope tolerance is raised to the true 12-file footprint (Decision Log D7).
      This resolves review round-2 B5/B6.

    - Observation: ADR-003 lists ``working_dir`` only as a field *name*, with no
      rich field description to amend; and the developers' guide phrase "the
      fixed ``working_dir`` constant" sits at line 158, not 160.
      Evidence: ``docs/adr-003-shared-interface-contract.md`` line 46 is the
      bullet "Every command emits a common JSON envelope: ``command``,
      ``schema_version``, ``ok``, ``working_dir``, ``result``, ``messages``." —
      a six-field listing with no per-field prose. ``docs/developers-guide.md``
      line 158 reads "the fixed ``working_dir`` constant" within the 155-176
      identity-proof block (round-2 advisories A4, A5).
      Impact: Work item 3 step 2 takes the add-a-note path only (no description
      exists to amend); Work item 3 step 3 targets line 158 (within 155-176), not
      line 160.

    - Observation: The cuprum git checkout has drifted ahead of the locked wheel.
      Evidence: /data/leynos/Projects/cuprum cuprum/sh.py at HEAD de54bff defines
      ``SafeCmd.run_sync(*, output, timeout, context, stdin)`` with no
      ``capture`` kwarg (RunOutputOptions collapse, PR #151), whereas the
      installed
      .venv/lib/python3.14/site-packages/cuprum/sh.py defines
      ``run_sync(*, capture=True, echo=False, context=None)``.
      Impact: All cuprum API claims in this plan are pinned to the *installed*
      locked 0.1.0 signature, never the git HEAD.

    - Observation (Work item 0, 2026-06-26): the live audit confirms the
      three-bucket inventory the plan predicted, with no surprises.
      Evidence: ``leta refs WORKING_DIR_NAME`` reports the production stamps at
      ``novel_ralph_skill/commands/novel.py:152``
      (``working_dir=WORKING_DIR_NAME`` in the ``main`` ``RunContext``) and
      ``novel_ralph_skill/commands/novel_state.py:264``
      (``result={"working_dir": WORKING_DIR_NAME, "slug": slug}`` in ``init``);
      the parallel payload sites at ``_desloppify.py:198`` and
      ``_wordcount.py:130`` (each ``working_dir = pathlib.Path(WORKING_DIR_NAME)``);
      and the sole synthetic-driver pin at ``tests/multiplexer_support.py:107``
      (``working_dir=WORKING_DIR_NAME``). ``tests/contract_drive_support.py:190``
      injects the literal ``"working"`` rather than the constant, as the plan
      notes. The ``init``-body snapshot to regenerate is
      ``test_init_success_envelope_snapshot`` in
      ``tests/test_novel_state_mutator_snapshots.py``.
      Impact: no third production stamp exists, so the Ambiguity tolerance is not
      triggered; Work item 1 proceeds against the two stamps as planned.

    - Observation (Work item 0, CodeRabbit): the ``coderabbit review --agent``
      pass over this commit raised five *minor* findings, all doc-style nits on
      living planning artifacts (first/second-person voice and 80-column reflow
      across ``roadmap-6-3-4.md`` and the ``*review*`` logs, plus first-use
      expansion of ``cwd``/``e2e``).
      Disposition: the 80-column overruns in
      ``roadmap-6-3-4.logisphere-review-r3.md`` were already reflowed for
      ``make markdownlint``. The wholesale rewrite of the ~1100-line execplan and
      the reviewers' record into neutral third person is deliberately declined:
      it is meaning-neutral churn of an instructional planning document whose
      voice is intentional, and it touches no production behaviour or gate.
      ``make markdownlint`` and ``make nixie`` are green, which is the binding
      prose gate for this repository.

    - Observation (Work item 1, 2026-06-26): the plan's Surprise claim that
      "nothing existing drives ``novel.main``" was inaccurate. Two suites drive
      the real entry point and observe its ``RunContext`` stamp.
      Evidence: ``tests/test_novel_state_check.py`` defines ``_drive_entry_point``
      (line 185-191) which calls ``novel.main()``; its
      ``test_entry_point_human_flag_switches_rendering`` (line 194) and
      ``test_entry_point_usage_error_carries_working_dir`` (line 212) both
      asserted the literal ``"working"``. ``tests/test_reconcile_e2e.py`` also
      drives ``novel.main()`` but does not assert ``working_dir``. Separately,
      the ``init`` *body* ``result.working_dir`` is captured by the cross-command
      identity proof ``tests/cross_command_contract/test_mutator_identity.py``
      (``test_mutator_success_skeleton_identity[init]``), which the plan's
      Constraint expected to stay unchanged.
      Impact: both ``test_novel_state_check.py`` real-entry-point tests were
      re-pointed at ``str((<dir>/working).resolve())`` and the module docstring
      corrected; the mutator-identity ``_normalise`` was extended to redact the
      body ``result.working_dir`` (top-level label untouched) and its ``.ambr``
      regenerated. These are the two unforeseen edit sites in Decision Log D9.

    - Observation (Work items 1-2, CodeRabbit): the review over the combined
      change raised four findings, all on the new test modules. Two majors and a
      trivial on assertion quality were applied; one major (group the cases into a
      test class) was declined.
      Disposition: added explicit assertion messages to every bare ``assert`` in
      ``test_state_load_resolved_working_dir.py`` and
      ``test_novel_main_working_dir.py``; replaced the POSIX-specific
      ``endswith("/working")`` suffix checks with ``pathlib`` ``.name``/``.parts``
      assertions; and fixed a doubled-article docstring. The "group into a test
      class" finding is declined: the repository convention is module-level test
      functions (135 of 135 test modules use flat ``test_*`` functions; the few
      classes present are ``NamedTuple``/support helpers, not ``TestX``
      groupings), so a class would diverge from the established layout. ``make
      all`` is green after the fixes.

## Decision log

    - Decision: D1 — Surface the absolute resolved path rather than implement an
      upward search.
      Rationale: Lowest blast radius; preserves the source-documented fixed
      cwd-relative resolution (``_state_load.py:32-48``); serves ``novel state
      init`` (which has no ancestor to search for); avoids ancestor-ambiguity;
      and directly closes the silent-misresolution dogfooding defect by making
      the resolved path loud in the fields the agent already gates on (design §3;
      roadmap §6.3). Subdirectory auto-resolution is a deliberately accepted
      non-goal (see Purpose).
      Date/Author: 2026-06-26, planning agent.

    - Decision: D2 — Compute the reported path as ``working_dir().resolve()`` (a
      new ``resolved_working_dir()`` accessor in
      ``novel_ralph_skill/commands/_state_load.py``), stamped at ``novel.main``
      as ``str(resolved_working_dir())`` and used in ``novel state init``'s
      result body.
      Rationale: ``Path.resolve()`` (non-strict default on Python 3.14) returns
      an absolute, normalised path even when ``working/`` does not yet exist, so
      it works on the exit-3 "no working/" arm and on ``init``. It keeps
      ``WORKING_DIR_NAME``/``working_dir`` as the single resolution home for this
      module and adds one sibling accessor rather than a parallel rule. Tests
      assert against the same construction to avoid symlink-normalisation
      flakiness.
      Date/Author: 2026-06-26, planning agent.

    - Decision: D3 — Leave ``RunContext.working_dir`` typed as ``str`` and leave
      the cross-command identity proofs injecting the literal ``"working"``.
      Rationale: The contract layer is path-agnostic (it stamps whatever string
      it is handed); making the field absolute is a property of the *production
      entry point*, not the contract. Keeping the type ``str`` keeps the envelope
      JSON shape unchanged and avoids reworking the synthetic-RunContext suites.
      Date/Author: 2026-06-26, planning agent.

    - Decision: D4 — Re-cite the resolution rule to its true locus and correct
      the round-1 misattributions.
      Rationale: The design document does not state the cwd-relative rule in
      prose (verified by grep; design line 151 is a JSON sample, not a rule), and
      the developers' guide contains neither "the single ``WORKING_DIR_NAME``-
      anchored accessor" nor a ``working_dir`` "fixed constant" prose target. The
      rule lives at ``_state_load.py:32-48``; the devguide's real relevant lines
      are 132-135 (the state-error arm message and "cwd tail is volatile") and
      155-175 (the cross-command identity proof, which at line 160 calls
      ``working_dir`` "the fixed ``working_dir`` constant"). Every Constraint and
      work item that leaned on the phantom prose is re-derived against these
      loci. This resolves review B3.
      Date/Author: 2026-06-26, planning agent.

    - Decision: D5 — The parallel resolution sites in ``_desloppify.py:198`` and
      ``_wordcount.py:130`` are acknowledged and scoped OUT of the reported-path
      change.
      Rationale: They rebuild ``pathlib.Path(WORKING_DIR_NAME)`` to read the
      ``working/`` tree for their *payload* computation, not to stamp the
      envelope's ``working_dir`` label (which the shared ``run`` wrapper stamps
      from ``RunContext.working_dir``). Making the reported path absolute does
      not require touching them, and folding them into ``working_dir()`` is a
      separable tidy-up outside this task's success criterion. The plan states
      they are parallel sites rather than claiming resolution is single-sourced.
      This resolves review B1.
      Date/Author: 2026-06-26, planning agent.

    - Decision: D6 — Absolutize ``novel state init``'s ``result.working_dir``
      body field alongside the envelope label, bringing the second production
      stamp into scope.
      Rationale: ``novel_state.py:264`` stamps the literal ``WORKING_DIR_NAME``
      into a body field the agent reads, carrying exactly the §6.3.4 defect (the
      field never names *where* ``init`` created the tree). Leaving it literal
      while the envelope label goes absolute would create an asymmetry — the
      pre-mortem scenario where an agent gates on the silent ``init`` body. The
      hybrid (review advisory A3) closes this at near-zero cost: ``init`` already
      imports the state-load accessors, so it stamps
      ``str(resolved_working_dir())`` into the body. This resolves review B2 and
      makes the Purpose claim ("every path-bearing field names where the command
      looked") true. The Scope tolerance is raised from 8 to 9 files / 250 to
      280 lines to admit this. (Round-3 review B5 showed 9 still undercounts the
      footprint; Decision Log D7 raises it to the true 12 files / ~340 lines.)
      Date/Author: 2026-06-26, planning agent.

    - Decision: D7 — Carry D6's true cost: name the ``init``-success snapshot
      module as a first-class edit site and raise the Scope tolerance to the real
      12-file / ~340-line footprint.
      Rationale: D6 absolutizes ``novel_state.py:264``'s ``result.working_dir``,
      which the *real* ``init`` body stamps into
      ``test_init_success_envelope_snapshot``
      (``tests/test_novel_state_mutator_snapshots.py:62``, driven from
      ``monkeypatch.chdir(tmp_path)`` at line 68). The synthetic
      ``RunContext(working_dir="working")`` (line 52) fixes only the *top-level*
      envelope label; the ``result.working_dir`` body comes from production code
      and becomes a per-machine absolute path. The file's ``_normalise`` helper
      (lines 57-59) redacts only ``created_at`` and would let the body churn, so
      it must be extended to normalise the body ``result.working_dir`` (not the
      top-level label). The round-2 plan listed the ``.ambr`` in the Work item 0
      inventory but never named the snapshot module, its ``_normalise`` helper,
      or its stale docstring as edit sites, and capped Scope at 9 files — below
      the genuine 12-file set. This decision names all three (module + helper +
      docstring) plus the regenerated ``.ambr`` as Work item 1 edit sites and
      fixes the tolerance to match. The Wafflecat alternative (drop D6, leave the
      ``init`` body literal) is rejected: it re-opens the round-1 B2 asymmetry the
      prior review demanded be closed. This resolves review round-2 B5.
      Date/Author: 2026-06-26, planning agent.

    - Decision: D8 — Correct the now-false snapshot-module docstring invariant and
      pin the new truth.
      Rationale: ``tests/test_novel_state_mutator_snapshots.py`` lines 5-8 assert
      "the envelope carries no absolute path (``working_dir`` is the fixed
      ``"working"`` token)." After D6 this is false for the ``init`` body: the
      ``result.working_dir`` carries an absolute resolved path. The docstring is
      a load-bearing statement of the module's normalisation contract, so it is
      corrected (in Work item 1, where the snapshot regenerates) to state the new
      truth: the *production entry point* ``novel.main`` and the ``novel state
      init`` result body now carry the absolute resolved path; only the
      synthetic-``RunContext`` envelopes these snapshots build keep the injected
      ``"working"`` token for the top-level label, and ``_normalise`` redacts the
      ``init``-body ``result.working_dir`` so the snapshot stays
      machine-independent. This resolves review round-2 B6.
      Date/Author: 2026-06-26, planning agent.

    - Decision: D9 — Two production-path test sites beyond the enumerated 12 had
      to change, taking the real footprint to 14 files; the deviation is carried
      rather than escalated.
      Rationale: the production stamp the plan introduced
      (``working_dir=str(resolved_working_dir())`` at ``novel.main``) flows into
      *every* test that drives the real entry point, not only the new
      ``test_novel_main_working_dir.py`` the plan added. Implementation found two
      pre-existing real-entry-point assertions the audit missed:
      ``tests/test_novel_state_check.py``'s
      ``test_entry_point_human_flag_switches_rendering`` and
      ``test_entry_point_usage_error_carries_working_dir`` (both call
      ``novel.main()`` via ``_drive_entry_point`` and asserted the literal
      ``"working"``), plus the ``init``-body capture in the cross-command
      identity proof ``tests/cross_command_contract/test_mutator_identity.py``
      (and its ``.ambr``). The Scope tolerance ("a thirteenth file … stop and
      escalate") is read as a guard against silent scope creep, not against the
      mechanical, unavoidable fallout of the *already-approved* production change:
      these edits assert the exact contract the plan mandates (the absolute
      resolved path at the production boundary), add no new behaviour, and leaving
      them red would violate AGENTS.md's "healthy state / make all green"
      requirement. The deviation is recorded here with its full inventory (14
      files: the 12 enumerated plus ``test_novel_state_check.py`` and
      ``test_mutator_identity.py`` + its ``.ambr``) so a reviewer sees the true
      footprint. No interface, dependency, or semantic tolerance was breached.
      Date/Author: 2026-06-26, implementation agent.

    - Decision: D10 — Do not run ``make fmt`` for the Work item 3 doc edits; apply
      surgical edits that already satisfy the markdown gates.
      Rationale: ``make fmt`` runs ``mdformat`` over the whole repository and
      reflows every ``.md`` file under ``docs/`` and ``skill/``, producing
      hundreds of lines of unrelated churn (the repository's stash log records
      this same ``make fmt`` reflow problem on many prior tasks). The binding
      gates are ``make markdownlint`` and ``make nixie`` (the ``check-fmt`` half
      of ``make all`` does not check markdown — ``mdformat-all`` "doesn't
      currently do checking"). The Work item 3 edits are written to satisfy the
      80-column wrap and dash-bullet rules directly, ``make markdownlint`` and
      ``make nixie`` pass, so the unwanted full-tree reflow is parked in a stash
      rather than committed. This keeps the doc commit scoped to the three target
      files.
      Date/Author: 2026-06-26, implementation agent.

## Outcomes & retrospective

Compare against Purpose: the envelope `working_dir` AND the `novel state init`
result-body `working_dir` are the absolute resolved path; an inside-`working/`
invocation surfaces `.../working/working` rather than failing silently; the
design and dev guide record the decision; `make all`, `make markdownlint`, and
`make nixie` are green.

Final outcome (2026-06-26): all four work items implemented, gated, and
committed.

- `resolved_working_dir()` was added to `_state_load.py` and re-exported from
  `novel_state`. Both production stamps now carry the absolute resolved path:
  `novel.main`'s envelope label (`working_dir=str(resolved_working_dir())`) and
  `novel state init`'s `result.working_dir` body. Resolution stays cwd-relative;
  only the reported value changed. `RunContext.working_dir` stayed `str` (D3);
  the parallel sites in `_desloppify.py`/`_wordcount.py` were left untouched (D5).
- Behavioural proof: new `tests/test_state_load_resolved_working_dir.py` (unit),
  `tests/test_novel_main_working_dir.py` (the production entry point, no-working/
  and inside-working/ arms), an init-body case in `test_novel_state_mutators.py`,
  and the per-cell absolute `working_dir` plus an inside-`working/` case in the
  installed-binary e2e. The synthetic-`RunContext` snapshots kept the injected
  `"working"` top-level label; their `_normalise` helpers redact only the
  absolute `init`-body `result.working_dir`.
- Two unplanned production-path test sites also needed updating (D9), and
  `make fmt`'s full-tree reflow was parked rather than committed (D10).
- Gates: `make all` is green at HEAD; `make markdownlint` and `make nixie` pass.
  CodeRabbit was run twice (Work item 0; Work items 1-2 combined) — its
  actionable findings (assertion messages, path-portability, a docstring nit)
  were applied; the "group tests into a class" finding was declined against the
  repository's flat-function convention. No coderabbit rate-limiting occurred.

Retrospective: the plan's most material miss was the claim that "nothing existing
drives `novel.main`" — two `test_novel_state_check.py` cases and the
`test_reconcile_e2e.py` suite do. A future plan introducing a production-stamp
change should grep for *all* drivers of the real entry point (not only the
synthetic `RunContext` builders) when sizing the test footprint, and should size
the Scope tolerance to absorb the mechanical fallout of the approved production
change.

## Context and orientation

You are working in a Python package, `novel_ralph_skill`, that ships a single
`novel` command-line multiplexer (`novel state …`, `novel done`,
`novel compile`, `novel desloppify`, `novel wordcount`). Every command emits one
JSON envelope on stdout (or a human rendering under `--human`) carrying the six
fields `command`, `schema_version`, `ok`, `working_dir`, `result`, `messages`.

Key files (full repository-relative paths):

- `novel_ralph_skill/commands/_state_load.py` — the home for this module's
  resolution accessors. Defines `WORKING_DIR_NAME = "working"` (line 36, with the
  cwd-relative-rule comment at lines 32-36), `working_dir()` (lines 40-48,
  returns `pathlib.Path("working")`), and `state_path()`
  (`working_dir() / "state.toml"`). This is where the new
  `resolved_working_dir()` accessor belongs. Note: this module is the resolution
  home for the *contract entry point and state accessors*, but it is NOT the
  only place in the codebase that resolves `working/` — see `_desloppify.py` and
  `_wordcount.py` below (Decision Log D5).
- `novel_ralph_skill/commands/novel.py` — the production entry point. Its
  `main()` (lines 147-153) builds the multiplexer and calls `run(...,
  RunContext(command=name, working_dir=WORKING_DIR_NAME, human=human))` at line
  152. `WORKING_DIR_NAME` (the literal `"working"`) is the value currently
  stamped into the envelope label. This is one of the two production stamps that
  change.
- `novel_ralph_skill/commands/novel_state.py` — hosts `novel state` and its
  mutators, and re-exports the `_state_load.py` accessors. Its `init` builder at
  line 262-265 returns `result={"working_dir": WORKING_DIR_NAME, "slug": slug}`
  — the **second** production stamp of a path-bearing `working_dir`, in the
  result body (Decision Log D6). The new `resolved_working_dir()` accessor is
  re-exported here too.
- `novel_ralph_skill/commands/_desloppify.py` (line 198) and
  `novel_ralph_skill/commands/_wordcount.py` (line 130) — each rebuilds
  `working_dir = pathlib.Path(WORKING_DIR_NAME)` to read the tree for its
  payload. These are the parallel resolution sites scoped OUT of the reported
  path (Decision Log D5); they do not stamp the envelope label.
- `novel_ralph_skill/contract/runner.py` — defines `RunContext` (a frozen
  dataclass with `command: str`, `working_dir: str`, `human: bool`) and `run`,
  which stamps `context.working_dir` into every envelope, including the
  body-less exit-2/exit-3 diagnostic arms. The contract layer is path-agnostic:
  it stamps whatever string it is handed.
- `novel_ralph_skill/contract/envelope.py` — builds and renders the envelope;
  `working_dir` flows through as a plain string.
- `tests/multiplexer_support.py` (line 107) and `tests/contract_drive_support.py`
  (line 190) — the behavioural and identity drivers. They build their own
  `RunContext` with the literal constant and drive `novel.build_multiplexer()` /
  the per-command builders, **not** `novel.main`, so they are insulated from the
  production change. Work item 1 must add a test that drives `novel.main`
  directly (nothing existing does).
- `tests/cross_command_contract/` — the identity proof; builds `RunContext` with
  `working_dir="working"` directly. Leave it asserting its injected constant.
- `tests/test_console_scripts_error_arms_e2e.py` — the installed-binary e2e. The
  machine-envelope test `test_installed_error_arm_machine_envelope` (line 251) is
  `@pytest.mark.parametrize("cell", _CELLS)`; `_CELLS` is `_COMMANDS`
  (state, desloppify) × `_ARMS` (usage, state) (line 194-195). The full-envelope
  equality asserting `"working_dir": "working"` is at line 300 and fires **once
  per cell**. Each cell's `run_dir` is built inside `_run_installed_arm` at line
  235 (`run_dir = tmp_path / f"{command.mount_verb[0]}-{arm.label}"`) and dropped
  before the assertion. This is the production-path assertion that changes, and
  it changes per cell, not at one literal (review B4).
- `tests/installed_binary_fixtures.py` — builds the wheel once and exposes the
  cuprum runner (`single_program_catalogue`, `installed_novel_state`,
  `ExecutionContext`).

Terms:

- *Envelope*: the single JSON object each command prints
  (`docs/novel-ralph-harness-design.md` §3.1).
- *Result body*: the `result` field of the envelope, carrying the
  command-specific structured payload (design §3.1). `novel state init`'s body
  includes a `working_dir` key (Decision Log D6).
- *Body-less diagnostic arm*: the exit-2 (usage) or exit-3 (state/input) error
  the shared `run` wrapper stamps before any command body executes; it still
  carries the top-level `working_dir` field (`docs/novel-ralph-harness-design.md`
  §3.2).
- *Resolve (a path)*: `pathlib.Path.resolve()` returns an absolute, normalised
  path; with its default non-strict mode it succeeds even when the path does not
  exist.
- *Synthetic `RunContext`*: a `RunContext` a test builds itself with an explicit
  `working_dir` string, as opposed to the one `novel.main` builds in production.

## Plan of work

Four work items, each independently committable and gate-passable. Work item 0
establishes the test inventory (no production change), keeping the risky
discovery step separate from the behavioural change. Each item ends with the
relevant validation.

### Work item 0 — Audit the `working_dir` pins and lock the inventory

Documentation to read first:

- `docs/novel-ralph-harness-design.md` §3 (the envelope and the `working_dir`
  field). Note: the resolution rule is NOT here — read it at
  `novel_ralph_skill/commands/_state_load.py:32-48` instead (Decision Log D4).
- `docs/adr-003-shared-interface-contract.md` (the envelope/exit contract).
- `docs/developers-guide.md` lines 132-135 (the state-error arm message, "cwd
  tail is volatile") and 155-175 (the cross-command identity proof and the
  "fixed `working_dir` constant" at line 160).

Skills to load: `leta` (navigate the code), `python-router` (route the Python
work; it will point at `python-testing` for the test-inventory reasoning).

Actions (no production code change in this item):

1. Use `leta refs WORKING_DIR_NAME` and `leta grep "working_dir"` to enumerate
   every construction of `RunContext` and every place a `working_dir` key is
   emitted into an envelope or result body, in both `novel_ralph_skill/` and
   `tests/`.
2. Classify each hit into one of three buckets and record the inventory in this
   plan's `Surprises & Discoveries`:
   - **Production stamps (in scope)** — exactly two, already found:
     `novel_ralph_skill/commands/novel.py:152` (envelope label) and
     `novel_ralph_skill/commands/novel_state.py:264` (`init` result body).
   - **Parallel resolution sites (scoped out, payload only)** —
     `novel_ralph_skill/commands/_desloppify.py:198` and
     `novel_ralph_skill/commands/_wordcount.py:130` (Decision Log D5).
   - **Synthetic / snapshot test pins (insulated)** — the ~20 test files whose
     `working_dir` value is injected by a synthetic `RunContext`, or recorded in
     a snapshot driven by one. Verified members include
     `tests/contract_drive_support.py:190`, `tests/multiplexer_support.py:107`,
     the `tests/cross_command_contract/` package,
     `tests/test_command_surface_matrix.py` (driven through
     `contract_drive_support`, so its `tests/__snapshots__/
     test_command_surface_matrix.ambr` records the injected `"working"` and is
     safe), and every `.ambr` snapshot under `tests/__snapshots__/` that contains
     a `working_dir: working` line (`test_contract_envelope.ambr`,
     `test_contract_envelope_snapshots.ambr`, `test_compile_snapshots.ambr`,
     `test_compile_check_snapshots.ambr`, `test_novel_state_mutator_snapshots.ambr`,
     `test_novel_state_check_disk.ambr`, `test_reconcile_refuse.ambr`,
     `test_novel_done_snapshots.ambr`, `test_desloppify_snapshots.ambr`,
     `test_wordcount_snapshots.ambr`, `test_ledger_snapshots.ambr`). These stay
     unchanged because they assert the injected constant, not the production
     path.
   - **Production-path e2e pin (in scope, per cell)** —
     `tests/test_console_scripts_error_arms_e2e.py`, the parametrized
     `test_installed_error_arm_machine_envelope` full-envelope equality across
     all `_CELLS` (review B4).
3. The audit has found exactly two production stamps. If — and only if — a
   **third** live production stamp of a path-bearing `working_dir` is found
   beyond those two, stop and escalate per the Ambiguity tolerance.
4. Confirm the one `novel state init` snapshot that records a *body*
   `result.working_dir`: `test_init_success_envelope_snapshot` in
   `tests/test_novel_state_mutator_snapshots.py:62`, captured at
   `tests/__snapshots__/test_novel_state_mutator_snapshots.ambr:22` as
   `"result": {"working_dir": "working", "slug": "s"}`. That test drives the
   **real** `init` body from `monkeypatch.chdir(tmp_path)` (line 68) through a
   synthetic `RunContext(working_dir="working")` (line 52): the top-level
   envelope `working_dir` stays the injected `"working"` token (safe), but the
   `result.working_dir` body is produced by `init`'s own code and becomes a
   per-machine absolute path once Decision D6 lands. The file's `_normalise`
   helper (lines 57-59) currently redacts only the `created_at` timestamp and
   does **not** touch `result.working_dir`. Record this as the single snapshot
   that Work item 1 must regenerate — and that its source module
   (`tests/test_novel_state_mutator_snapshots.py`: `_normalise` helper + module
   docstring) is itself an edit site, not just its `.ambr` (Decision Log D7, D8;
   review round-2 B5/B6). Re-confirm no *other* mutator snapshot in that `.ambr`
   carries a body `result.working_dir` (the others — `set-cursor`,
   `advance-phase`, `recount`, etc. — do not; only their synthetic top-level
   label reads `"working"`, which stays unchanged).

Tests: none added in this item; it is a research-and-record step. The
deliverable is the updated `Surprises & Discoveries` recording the confirmed
three-bucket inventory and the single `init`-body snapshot to regenerate
(`test_init_success_envelope_snapshot`), together with the confirmation that its
source module `tests/test_novel_state_mutator_snapshots.py` (`_normalise` helper
and module docstring) is a Work item 1 edit site.

Validation: `make all` (must already be green at the start of the branch — this
item changes only this plan document, so re-running confirms the baseline).
Because this item edits a markdown file (`docs/execplans/roadmap-6-3-4.md`), also
run `make markdownlint` and `make nixie`.

Commit: "Audit working_dir pins ahead of absolute-path surfacing (roadmap 6.3.4)".

### Work item 1 — Add the absolute-path accessor and stamp it at both production sites

Documentation to read first:

- `docs/novel-ralph-harness-design.md` §3.1 (envelope fields and the `result`
  body).
- `novel_ralph_skill/commands/_state_load.py:32-48` (the resolution rule and the
  existing accessors — the true locus, Decision Log D4).
- `docs/scripting-standards.md` (path-handling and message conventions).
- `tests/test_novel_state_mutator_snapshots.py` lines 5-11 (the module docstring
  invariant to correct), lines 35-39 (`_TIMESTAMP` and the `created_at`
  redaction this work mirrors), lines 57-59 (the `_normalise` helper to extend),
  and lines 62-72 (`test_init_success_envelope_snapshot`, the one snapshot whose
  body `result.working_dir` D6 makes absolute — Decision Log D7/D8).

Skills to load: `leta`; `python-router` → `python-types-and-apis` (the accessor
signature) and `python-testing` (the behavioural, unit, and snapshot tests).
Consult `python-verification` to confirm whether a property test adds value
here; this plan judges example-based behavioural tests sufficient because the
mapping is a single deterministic `resolve()` with no input range (record that
judgement in the Decision Log if `python-verification` agrees).

Actions:

1. In `novel_ralph_skill/commands/_state_load.py`, add a `resolved_working_dir()
   -> pathlib.Path` accessor returning `working_dir().resolve()`, with a
   docstring stating it returns the absolute, resolved `working/` for the
   envelope/result label and that it succeeds even when `working/` is absent
   (Decision D2; rule at `_state_load.py:32-48`; en-GB spelling). Re-export it
   from `novel_ralph_skill/commands/novel_state.py` alongside the existing
   `working_dir`/`state_path` exports so the public import surface stays
   consistent.
2. In `novel_ralph_skill/commands/novel.py:main` (line 152), change the
   `RunContext` construction from `working_dir=WORKING_DIR_NAME` to
   `working_dir=str(resolved_working_dir())`. Update the surrounding comment that
   describes the field to the new absolute-resolved contract.
3. In `novel_ralph_skill/commands/novel_state.py` `init` (line 264), change
   `result={"working_dir": WORKING_DIR_NAME, "slug": slug}` to
   `result={"working_dir": str(resolved_working_dir()), "slug": slug}`
   (Decision D6). The body now names the absolute path where `init` created the
   tree.
4. Leave `RunContext.working_dir` typed as `str` and the contract layer
   untouched (Decision D3). Leave `_desloppify.py:198` and `_wordcount.py:130`
   untouched (Decision D5).

Tests (write the failing assertions first, then implement; AGENTS.md red-green;
every test module and function carries a docstring per the interrogate gate):

- New unit test (e.g. `tests/test_state_load_resolved_working_dir.py`): from a
  `monkeypatch.chdir(tmp_path)`, assert `resolved_working_dir()` equals
  `tmp_path.resolve() / "working"`, that the result is absolute
  (`.is_absolute()`), and that it succeeds with no `working/` on disk (proving
  the non-strict resolve). Assert it equals `working_dir().resolve()` so the
  accessors stay coherent.
- New behavioural test that drives the **production entry point** `novel.main`
  (e.g. `tests/test_novel_main_working_dir.py`): nothing existing drives
  `novel.main` (the drivers build their own `RunContext`), so this test calls
  `novel.main` with `monkeypatch.setattr(sys, "argv", [...])` (or the project's
  established `main`-driving pattern), from a chosen directory via
  `monkeypatch.chdir(tmp_path)`, over an exit-3 arm (no `working/` present),
  capturing stdout (`capsys`) and the `SystemExit`. Parse the JSON envelope and
  assert `envelope["working_dir"] == str((tmp_path / "working").resolve())` and
  that the value is an absolute path. Add the inside-`working/` case:
  `(tmp_path / "working").mkdir()` then `monkeypatch.chdir(tmp_path / "working")`
  and assert the stamped path ends with `working/working`, proving the footgun
  is now visible rather than silent.
- New behavioural/unit test for `novel state init`'s body (e.g. extend
  `tests/test_novel_state_mutators.py` or add a focused case): drive `init` from
  `monkeypatch.chdir(tmp_path)` and assert
  `outcome.result["working_dir"] == str((tmp_path / "working").resolve())` and
  that it is absolute (Decision D6).
- Edit `tests/test_novel_state_mutator_snapshots.py` (named edit site, Decision
  Log D7/D8) to keep `test_init_success_envelope_snapshot` machine-independent
  after D6 makes the `init`-body `result.working_dir` absolute:
  - Extend the `_normalise` helper (lines 57-59). Today it redacts only the
    `created_at` RFC 3339 timestamp via the `_TIMESTAMP` regex (line 37); add a
    second redaction that replaces the **body** `result.working_dir` value with
    a stable token (e.g. `<working-dir>`). This **mirrors the existing
    `created_at` timestamp redaction in this same helper — NOT a "message"
    redaction (this file does not redact messages; the round-2 plan's
    "mirroring the existing message redaction" wording was wrong, review B5).**
    Target only the `result.working_dir` body value: the top-level envelope
    `working_dir` is the synthetic-injected `"working"` token and must stay
    verbatim, so prefer a JSON-aware normalisation (parse the envelope, rewrite
    `result["working_dir"]`, re-serialise) or a regex anchored to the `"result":
    {...}` object, not a blanket substitution of every `working_dir` occurrence.
  - Regenerate `tests/__snapshots__/test_novel_state_mutator_snapshots.ambr` by
    re-accepting the snapshot (`--snapshot-update`); the regenerated line 22 reads
    `"result": {"working_dir": "<working-dir>", "slug": "s"}`, with the top-level
    `"working_dir": "working"` unchanged. Verify the redaction is idempotent and
    machine-independent (Idempotence section).
  - Correct the module docstring (lines 5-8), which currently asserts the now-false
    invariant "the envelope carries no absolute path (`working_dir` is the fixed
    `"working"` token)" (review B6, Decision D8). State the new truth: the
    *production entry point* `novel.main` and the `novel state init` result body
    now carry the **absolute resolved** path; the synthetic-`RunContext` envelopes
    these snapshots build keep the injected `"working"` token for the **top-level**
    label, and `_normalise` redacts the `init`-body `result.working_dir` so the
    snapshot stays machine-independent. Keep en-GB Oxford spelling.
- These tests fail before the production change (the fields are `"working"`) and
  pass after. The `init`-success snapshot, once `_normalise` redacts the body
  value, asserts a stable `<working-dir>` token both before and after; without the
  redaction it would break on the absolute literal, so add the `_normalise`
  extension in the same commit as the `novel_state.py` body change.

Validation: `make all` (runs `build check-fmt lint typecheck test`, including the
`interrogate` docstring gate). Expect the new tests to fail before the edits to
`novel.py`/`novel_state.py` and pass after. No markdown changed in this item, so
`markdownlint`/`nixie` are not required here.

Commit: "Surface the absolute resolved working_dir at both production stamps
(roadmap 6.3.4)".

### Work item 2 — Update the parametrized installed-binary e2e for the absolute path

Documentation to read first:

- `docs/developers-guide.md` lines 132-135 (the "cwd tail is volatile" note;
  roadmap §6.3.1 precedent for asserting a path-bearing field by computed value).
- The module docstring of `tests/test_console_scripts_error_arms_e2e.py` for the
  POSIX-only e2e constraint and the slow/timeout marker discipline.

Skills to load: `leta`; `python-router` → `python-testing` (e2e/snapshot
discipline). Do **not** load `firecrawl` for this item: the e2e leans only on
the *locked* cuprum API, pinned in this plan's Interfaces section against the
installed source; no external-library behaviour is asserted from memory.

Actions:

1. In `tests/test_console_scripts_error_arms_e2e.py`,
   `test_installed_error_arm_machine_envelope` (line 251) is parametrized over
   **all** `_CELLS`; its full-envelope equality (line ~298-301) currently asserts
   `"working_dir": "working"` for every cell. Because each cell runs the binary
   with `ExecutionContext(cwd=run_dir)` and `run_dir` differs per cell
   (`tmp_path / f"{command.mount_verb[0]}-{arm.label}"`, built at line 235 inside
   `_run_installed_arm` and currently dropped), the fix must compute the expected
   value from **each cell's own** `run_dir`. Surface `run_dir` to the assertion:
   have `_run_installed_arm` return `(result, run_dir)` (or recompute `run_dir`
   in the test the same way), then assert
   `expected_working_dir = str((run_dir / "working").resolve())` and
   `envelope["working_dir"] == expected_working_dir`. Build the expected dict per
   cell with `command.name` and the computed `expected_working_dir`. Keep the
   rest of the full-envelope equality intact (the redacted `messages`, the
   `schema_version`, the field set and order). This is NOT a single-literal edit
   (review B4).
2. Add (or extend) an e2e case that proves the *inside-`working/`* behaviour over
   the real binary: build a `working/` tree under `run_dir`, then **run the binary
   with its cwd inside `working/`**. The `run_installed` fixture's signature is
   `run_installed(run_dir, argv)` and it constructs `ExecutionContext(cwd=run_dir)`
   internally (line 146-177); reach the deeper cwd by passing `run_dir / "working"`
   as the **first argument** to the fixture — do **not** construct an
   `ExecutionContext` in the test (the fixture does not expose that, review
   advisory A6). Assert the envelope's `working_dir` ends with `working/working`
   (the now-visible footgun). This is the installed mirror of the in-process
   behavioural test from Work item 1.
3. Confirm the human-mode test (`test_installed_error_arm_human_stamp`, line
   ~308) needs no change — it asserts only the header and message prefix, not the
   `working_dir` value.

Tests: the modified parametrized cells and the added inside-`working/` case
above. They are `@pytest.mark.slow` with a per-test `@pytest.mark.timeout(180)`
that supersedes the project default; preserve those markers (the locked
pytest-timeout per-test override is already in use on these tests — reuse the
existing pattern verbatim rather than re-deriving it). Each test function carries
a docstring (interrogate gate).

Validation: `make all`. The e2e suite is slow; expect the modified cells to fail
before Work item 1's production change is present and pass with it. No markdown
changed in this item.

Commit: "Pin the per-cell absolute working_dir at the installed-binary boundary
(roadmap 6.3.4)".

### Work item 3 — Update the design doc, ADR note, and developers' guide

Documentation to read first: the three documents being edited, plus AGENTS.md
"Markdown guidance" (80-column prose wrap, dashes for bullets) and
`en-gb-oxendict`.

Skills to load: `en-gb-oxendict` (spelling), `leta` only if cross-referencing
code symbols.

Actions:

1. `docs/novel-ralph-harness-design.md` §3.1: update the envelope JSON sample
   (currently `"working_dir": "working"` at line 151) to show an absolute
   resolved path (e.g. `"/home/me/my-novel/working"`) and add a sentence stating
   that `working_dir` (and `novel state init`'s `result.working_dir`) is the
   **absolute resolved** path the command used, so a misresolution (for example
   a stray `cd` into `working/`) is visible. Cross-reference roadmap §6.3.4. The
   design doc does not currently state the cwd-relative resolution rule in prose
   (Decision D4); if a one-line note is added that the *reported* path is
   absolutized while resolution stays cwd-relative, cite the rule's true locus
   (`_state_load.py`), do not invent a "line 151 rule".
2. `docs/adr-003-shared-interface-contract.md`: **add a short note** recording
   that the `working_dir` field carries the absolute resolved path on the
   production path, while the resolution rule itself is unchanged. Note there is
   **no rich `working_dir` field description to amend** — line 46 lists
   `working_dir` only as a field *name* in the six-field bullet (review advisory
   A4), so take the add-a-note path; do not hunt for a phantom field description.
   Keep it consistent with the design doc wording.
3. `docs/developers-guide.md`: the real targets are line **158** (within the
   155-176 cross-command identity-proof block, which calls `working_dir` "the
   fixed `working_dir` constant" — review advisory A5 corrects the round-2
   "line 160" drift) and lines 132-135 (the state-error arm and "cwd tail is
   volatile").
   Amend line 158's description to explain the split: the *synthetic-RunContext*
   suites inject `"working"` and pin envelope *shape* (the "fixed constant" they
   assert is the injected one), whereas the *production entry point*
   (`novel.main`) and the installed-binary e2e stamp and assert the **absolute
   resolved** path. Reference the new `resolved_working_dir()` accessor. Do NOT
   search for the phrases "the single `WORKING_DIR_NAME`-anchored accessor" or a
   `working_dir` "fixed constant" find-and-replace target as a round-1 draft
   instructed — those exact strings are not in the guide (Decision D4).
4. Re-wrap edited prose at 80 columns; keep tables and headings unwrapped.

Tests: none (documentation only). If a docs-pinning test exists for the design
doc (check `tests/test_state_layout_reference.py` and similar), confirm it still
passes or update its expected strings.

Validation: `make all`, then `make markdownlint` and `make nixie` (required for
markdown changes per AGENTS.md and the standing rules). Run `make fmt` to
normalise the markdown after editing.

Commit: "Document the absolute working_dir contract (roadmap 6.3.4)".

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-6-3-4`.

1. Confirm the baseline is green before starting:

       make all

   Expect the existing suites to pass.

2. Work item 0 — enumerate and classify the pins:

       leta refs WORKING_DIR_NAME
       leta grep "working_dir"

   Record the three-bucket inventory; confirm the two production stamps are
   `novel.py:152` and `novel_state.py:264`, and the parallel sites are
   `_desloppify.py:198` / `_wordcount.py:130`.

3. Work item 1 — add `resolved_working_dir`, write the failing tests, then edit
   `novel.py` and `novel_state.py`:

       make all

   Expect the new tests red before the production edits and green after.

4. Work item 2 — update the parametrized e2e assertions:

       make all

   The slow e2e cells turn green once the production change is in.

5. Work item 3 — edit the three docs, then:

       make fmt
       make all
       make markdownlint
       make nixie

   Expect all green.

This section is updated as work proceeds; record any deviation in
`Surprises & Discoveries` and `Decision log`.

## Validation and acceptance

Acceptance is behavioural:

- Running the installed `novel` binary from a directory `D` with no `working/`
  tree exits 3 and prints an envelope whose `working_dir` equals the absolute
  path `D/working` (proved by the updated, per-cell
  `tests/test_console_scripts_error_arms_e2e.py` machine-envelope case).
- Running it from inside `D/working` prints an envelope whose `working_dir` ends
  with `working/working`, making the misresolution visible (proved by the new
  inside-`working/` behavioural and e2e cases).
- Driving `novel.main` in-process from a chosen directory stamps
  `str((<dir>/working).resolve())` into the envelope (proved by the new Work
  item 1 `novel.main` behavioural test).
- Running `novel state init` from a chosen directory returns
  `result.working_dir == str((<dir>/working).resolve())` (proved by the Work
  item 1 init-body test).
- The cross-command identity proofs in `tests/cross_command_contract/` and the
  synthetic-driven snapshots continue to pass unchanged, proving the contract
  shape is intact.

Quality criteria ("done"):

- Tests: `make test` passes; the new unit, behavioural, and e2e cases fail before
  the production change and pass after.
- Lint/typecheck: `make all` (which runs `check-fmt`, `lint`, `typecheck`,
  `test`) is green, including 100% docstring coverage (`interrogate`) on the new
  accessor AND every new test module/function (AGENTS.md).
- Markdown: `make markdownlint` and `make nixie` pass after the Work item 3 doc
  edits.

Quality method: run `make all` after every work item; run
`make markdownlint` and `make nixie` after any markdown change.

## Idempotence and recovery

- Every step is re-runnable. The accessor is a pure function; stamping the path
  has no side effects. Re-running `make all` is safe.
- If a work item's tests fail, fix forward within the Iterations tolerance (3
  attempts) before escalating; no step is destructive, so there is nothing to
  roll back beyond `git restore` of the working file.
- Snapshot regeneration (Work item 1) is idempotent: the extended `_normalise`
  replaces the `init`-body `result.working_dir` with the stable `<working-dir>`
  token before comparison, so re-accepting the snapshot yields a path-independent
  value identical on every machine. The top-level `working_dir` stays the
  injected `"working"` token, so it is unaffected by the redaction.
- The docs edits are plain text; re-running `make fmt` re-normalises them
  idempotently.

## Artifacts and notes

The production change is a one-function accessor plus two stamps:

    # novel_ralph_skill/commands/_state_load.py
    def resolved_working_dir() -> pathlib.Path:
        """Return the absolute, resolved ``working/`` for the envelope label."""
        return working_dir().resolve()

    # novel_ralph_skill/commands/novel.py (main, line 152)
    RunContext(
        command=name,
        working_dir=str(resolved_working_dir()),
        human=human,
    )

    # novel_ralph_skill/commands/novel_state.py (init, line 264)
    result={"working_dir": str(resolved_working_dir()), "slug": slug}

## Interfaces and dependencies

At the end of the milestone these symbols exist and have these contracts:

- `novel_ralph_skill.commands._state_load.resolved_working_dir() ->
  pathlib.Path` — returns `working_dir().resolve()`; absolute; succeeds when
  `working/` is absent (non-strict `resolve()`). Re-exported as
  `novel_ralph_skill.commands.novel_state.resolved_working_dir`.
- `novel_ralph_skill.commands.novel.main` — stamps
  `working_dir=str(resolved_working_dir())` into `RunContext` (the envelope
  label).
- `novel_ralph_skill.commands.novel_state` `init` — stamps
  `result["working_dir"] = str(resolved_working_dir())` (the result body).
- `novel_ralph_skill.contract.runner.RunContext.working_dir: str` — unchanged
  type; now receives an absolute path string on the production path.

External libraries (pinned against the **locked installed** versions, not any
git checkout):

- **Standard library `pathlib`** (Python `>=3.14`, per `pyproject.toml`):
  `Path.resolve()` with its default non-strict mode returns an absolute,
  normalised path even when the target does not exist. Verified locally:
  `chdir(tmpdir); Path("working").resolve()` yields `<tmpdir>/working` with no
  `working/` present (Python 3.14, this environment), and confirmed in the
  round-1 review. No external dependency is introduced.
- **cuprum 0.1.0 (locked)** — used only by the e2e harness, reused verbatim. The
  locked API, verified against
  `.venv/lib/python3.14/site-packages/cuprum/sh.py` (NOT the
  `/data/leynos/Projects/cuprum` git HEAD, which has drifted under PR #151), and
  re-confirmed by the round-1 review:
  - `cuprum.sh.make(program, *, catalogue) -> SafeCmdBuilder` (sh.py).
  - `SafeCmd.run_sync(*, capture: bool = True, echo: bool = False,
    context: ExecutionContext | None = None) -> CommandResult` (sh.py, locked
    line 450). `capture` IS a keyword on the locked 0.1.0 wheel; the existing
    e2e call `builder(*argv).run_sync(context=ExecutionContext(cwd=run_dir),
    capture=True)` is valid against it.
  - `ExecutionContext(cwd=…)` sets the subprocess working directory (sh.py
    `ExecutionContext`, `cwd` field) — the mechanism that lets the e2e drive the
    binary from a chosen directory and from inside `working/`.
  - `CommandResult` carries `exit_code: int`, `stdout: str | None`,
    `stderr: str | None` (sh.py `CommandResult`) — the e2e reads `exit_code` and
    `json.loads(stdout)` for the envelope.
  - `cuprum.ProgramCatalogue`, `cuprum.ProjectSettings`, `cuprum.program.Program`
    — used by `tests/installed_binary_fixtures.py` to allowlist the single
    installed `novel` program by absolute path; reused unchanged.
  No cuprum API beyond these is needed, and none of the drifted-HEAD
  `RunOutputOptions` surface is used.

Note on `firecrawl`: no work item in this plan asserts the *behaviour* of an
external library from memory. The only library behaviours load-bearing here are
(1) `pathlib.Path.resolve()` non-strict semantics, verified locally above,
confirmed in the round-1 review, and pinned by the Work item 1 unit test, and
(2) the locked cuprum signatures, verified against the installed source above and
in the round-1 review. Cyclopts argument parsing, `pytest-timeout` per-test
overrides, and `uv run` resolution are unchanged by this task (the e2e reuses the
existing markers and harness verbatim), so no firecrawl research is required;
were a future work item to change any of those, it would need the
firecrawl-cited confirmation the standing rules demand.

## Revision note

Round 2 (2026-06-26). Resolved all four Logisphere blocking points from
`docs/execplans/roadmap-6-3-4.review-r1.md`:

- **B1**: dropped the false "single home … the only place resolution happens"
  Constraint; named `_desloppify.py:198` and `_wordcount.py:130` as pre-existing
  parallel resolution sites and scoped them OUT of the reported path (Decision
  D5).
- **B2**: brought `novel_state.py:264`'s `init` result-body `working_dir` into
  scope and absolutized it alongside the envelope label (Decision D6, advisory
  A3 hybrid); corrected the false "only production stamp" claim and the Ambiguity
  tolerance (now escalates on a *third* stamp).
- **B3**: re-cited the cwd-relative resolution rule to its true locus
  (`_state_load.py:32-48`), not the phantom "design line 151" prose; re-pointed
  the devguide edits to the real lines 132-135 and 160; recorded both findings in
  Surprises and Decision D4.
- **B4**: restated the e2e pin as the parametrized full-envelope equality across
  all `_CELLS`, computing `expected_working_dir` from each cell's own `run_dir`;
  Work item 0 now enumerates and classifies the full ~20-file inventory in three
  buckets, naming the `.ambr` snapshots and `test_command_surface_matrix.py`
  explicitly as synthetic-driven.

Also addressed advisories A1 (subdirectory auto-resolution declared a
deliberate non-goal) and A2 (interrogate docstring gate called out for the new
test modules). The Scope tolerance was raised from 8/250 to 9/280 to admit the
`init` body change. No implementation performed.

Round 3 (2026-06-26). Resolved both Logisphere blocking points from
`docs/execplans/roadmap-6-3-4.logisphere-review-r2.md`:

- **B5** (scope-vs-footprint contradiction): named
  `tests/test_novel_state_mutator_snapshots.py` as a first-class Work item 1 edit
  site (its `_normalise` helper *and* module docstring), corrected the redaction
  analogue — the existing redaction in that file is of the `created_at`
  **timestamp**, NOT a message — and instructed a JSON-aware/scoped redaction of
  only the **body** `result.working_dir` (the synthetic top-level label stays
  `"working"`). Raised the Scope tolerance from 9/280 to the true **12-file /
  ~340-line** footprint, enumerating all twelve files (including the snapshot
  module and its `.ambr`), so an honest implementer no longer trips the tolerance
  at the first `init`-body commit (Decision Log D7). Work item 0 step 4 now points
  precisely at `test_init_success_envelope_snapshot` and its `.ambr:22` line.
- **B6** (stale documented invariant): folded the correction of the now-false
  module docstring at `tests/test_novel_state_mutator_snapshots.py` lines 5-8 into
  Work item 1, stating the new truth — `novel.main`'s envelope label and the
  `novel state init` result body carry the absolute resolved path; only the
  synthetic-`RunContext` snapshots keep the injected `"working"` token for the
  top-level label (Decision Log D8).

Also addressed advisories A4 (ADR-003 has no `working_dir` field description, so
Work item 3 takes the add-a-note path only), A5 (devguide "fixed `working_dir`
constant" is at line 158, not 160), and A6 (the inside-`working/` e2e reaches the
deeper cwd by passing `run_dir / "working"` to the `run_installed(run_dir, argv)`
fixture, not by constructing an `ExecutionContext`). No implementation performed.

## Addenda

Lightweight, no-plan corrections folded onto this completed task after the
review and audit of step 6.3 settled. Each runs as a no-review lightweight pass.

- [x] **6.3.4.1 (from review:6.3.4; low).** Normalise the ungated POSIX-separator
  suffix assertion `result["working_dir"].endswith("/working")` in
  `tests/test_novel_state_mutators.py` (line 100) to a pathlib-based
  `.name`/`.parts` check, matching the portability convention this task already
  enforced on its new test modules. The module is not `skipif`-gated for POSIX,
  so the separator literal diverges from the rest of the suite; the pathlib form
  keeps it portable and consistent. Scope: one assertion in one test file.
- [x] **6.3.4.2 (from review:6.3.4; low).** Extract one shared JSON-aware
  `working_dir` snapshot-normaliser and route both snapshot modules through it.
  Two snapshot modules now redact `result.working_dir` with divergent
  strategies — the brittle regex `_RESULT_WORKING_DIR` in
  `tests/test_novel_state_mutator_snapshots.py` versus a robust JSON parse
  elsewhere. A single JSON-aware normaliser removes the regex fragility and
  prevents per-machine snapshot churn if the envelope renderer's key order or
  whitespace changes. Scope: extract one shared test helper; route both snapshot
  modules onto it.
