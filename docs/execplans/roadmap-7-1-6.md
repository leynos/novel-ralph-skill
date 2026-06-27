# Settle the §7.1 authoritative-docstring + consumer self-projection convention with a reusable drift-guard

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DRAFT (planning round 4 — resolves the round-3 logisphere review's single
blocking finding B3-1, the vacuous tail-discriminator unit test, by co-locating
both spellings in the tail-isolating fixture; see Decision Log "tail-isolating
fixture co-locates both spellings (resolves B3-1)" and §"Source verification,
round 4". Rounds 2-3 already resolved R2-B1 / R2-B2 / R2-A1 / R2-A2; see Decision
Log "WI3 discriminator" / "registry coverage" / "compile_is_current
normalisation" / "no-bare-re-export check restated" and §"Source verification,
round 3")

## Purpose / big picture

Roadmap §7.1 ("Single-source the model, payload, and contract projections")
gives every task the same definition of done: the surviving canonical
projection "is documented as the single source of truth, and a test pins it so
it cannot silently re-fork". Tasks 7.1.1 through 7.1.4 each extracted one
canonical projection (the compile-currency predicate, the absent-file
`CompiledComparison` table, the `Reconciliation` payload, the shared
finding-outcome skeleton) and rerouted consumers through cross-referencing
docstrings. But the *documentation-and-test legs* of that invariant were
themselves left un-single-sourced (audit-7.1.2 Findings 2, 3, 5):

1. The authoritative cross-reference target is spelled two ways. Most consumers
   name the defining-module path
   (`novel_ralph_skill.state.compile_model.compiled_matches_drafts`), but
   `commands/_compile.py` names the re-export path
   (`novel_ralph_skill.state.compiled_matches_drafts`) in **eight** places —
   the module docstring (lines 12, 14, 34), `compile_manuscript`'s docstring
   (lines 104, 106), and `check_compiled`'s docstring (lines 175, 181, 186) —
   across the sibling `concatenate_drafts`/`present_draft_bodies`/
   `compiled_matches_drafts`/`CompiledComparison` symbols. Both spellings
   resolve, but the mixed spelling weakens the single-canonical-target intent
   and would dangle if the re-export were pruned. The same split exists for the
   reconciliation projection: `commands/novel_state.py::_render_reconciliation`
   names the re-export path `novel_ralph_skill.state.reconciliation_payload`
   while the defining module is
   `novel_ralph_skill.state.reconcile.reconciliation_payload`. A third, subtler
   variant lives in the authoritative module itself:
   `state/compile_model.py::compile_is_current` cross-references the
   authoritative table with a **bare relative** `:func:` role naming
   `compiled_matches_drafts` (line 106) rather than a dotted path,
   because it is intra-module. That bare relative ref names neither the canonical
   path nor the re-export path, so it satisfies neither the convention nor the
   guard; round 3 normalises it to the canonical defining-module path so the
   registry's consumer set is uniform (see Decision Log "compile_is_current
   normalisation").

2. No drift-guard pins the single-authoritative-copy invariant. The behavioural
   suites test the verdict (the truth table, the payload shape), not the prose.
   A future edit could re-expand any consumer's docstring back into a full
   projection table — re-introducing the precise duplication §7.1 removed — or
   break a cross-reference, and it would ship green.

After this change a reader can observe: every §7.1 consumer names its
authoritative target through the defining-module path (no re-export-path or
mixed spelling survives in production); one reusable drift-guard helper pins,
per consolidated projection, that the authoritative docstring carries the full
projection table while each consumer carries a resolving defining-module
cross-reference and none of the re-export spelling; and breaking or re-spelling
any consumer's cross-reference, or hollowing the authoritative table, reddens
the guard. This is doc-and-test only — no behaviour change.

The guard distinguishes the authoritative docstring from its consumers by
**registry position** (the authoritative symbol is the registry row's key), not
by parsing the prose for an "authority" token. This is forced by the real tree:
the bare phrases "single production site", "single source", and "authoritative
… table" all appear inside *consumer* docstrings as *references to* the
canonical site (`check_compiled` line 174 "from the single production site";
`_check_compiled_matches_drafts` line 196 "from the shared single production
site"; `compile_consistent` line 234 "the authoritative three-valued table"),
so no free-floating token tells authoritative from consumer. See the Decision
Log entry "WI3 discriminator".

Observable success: `make all` stays green, and the new guard test
`tests/test_projection_docstring_drift_guard.py` fails on a deliberately
re-expanded or mis-spelled consumer docstring and passes on the normalised tree
(red-before / green-after per work item).

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **Doc-and-test only; zero behaviour change.** No production control flow,
  signature, return value, exit code, or envelope datum may change. Only
  docstrings (prose) and test code may be edited in production files. The
  desloppify, compile, done-predicate, disk-evidence, and reconcile suites must
  stay green unchanged (roadmap 7.1.6 Success; design §4.3, §5.4).
- **The defining-module cross-reference path is canonical.** Every consumer
  must name its authoritative target via the *defining-module* dotted path
  (`novel_ralph_skill.state.compile_model.compiled_matches_drafts`,
  `novel_ralph_skill.state.reconcile.reconciliation_payload`), never the
  `state` re-export path. This is the convention audit-7.1.2 Finding 2 names
  and the roadmap Success criterion mandates.
- **Exactly one authoritative docstring per projection.** Each consolidated
  projection keeps a single full copy of its projection table in the defining
  symbol's docstring; consumers carry a resolving defining-module
  cross-reference plus a one-sentence self-projection. The guard ENFORCES this
  by registry position: it pins the table markers to the authoritative symbol
  and the cross-reference to each consumer. It does NOT forbid a consumer from
  *mentioning* member names (the real consumers are heterogeneous —
  `check_compiled` names all three, `_check_compiled_matches_drafts` two,
  `compile_consistent` none — so a member-count rule is unworkable; see
  Decision Log "WI3 discriminator"). The residual that a consumer could
  re-expand prose while keeping its cross-reference is accepted: the
  authoritative table stays the only *cited* source, so the projection cannot
  silently re-fork (the §7.1 definition of done), and WI4's documented
  convention plus review catch bloat.
- **The authoritative docstrings themselves must not be diluted.** Normalising
  the consumers must not strip content from `compiled_matches_drafts` /
  `reconciliation_payload`; their tables remain the single home.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all prose, comments, and
  commit messages, except where naming an external API verbatim (AGENTS.md;
  `en-gb-oxendict` skill). External-API exception note: Sphinx/`:func:`
  cross-reference *roles* and Python dotted *symbol paths* are code
  identifiers, not prose, and are reproduced verbatim.
- **No subprocess, no cuprum.** The drift-guard reads docstrings *in process*
  via the imported symbols' `__doc__`, mirroring the existing prose-guard
  pattern. It must not shell out and must not touch the console-script /
  cuprum-driven e2e harness (see Decision Log: cuprum is out of scope).
- **400-line file cap** (AGENTS.md). If the guard test plus its pure scanner
  approach the cap, split the parsing logic into a sibling helper module
  exactly as `tests/_skill_contract_scanner.py` does for
  `tests/test_skill_contract_drift_guard.py`.
- **Do not hard-depend on 7.1.5's code.** 7.1.6 `Requires 7.1.2, 7.1.3, 7.1.4`
  only; 7.1.5 may be unmerged when this lands (see Decision Log). The
  convention and guard must be authored so 7.1.5 can adopt them, but the guard
  must not import or assert against 7.1.5-only symbols.

## Tolerances (exception triggers)

- **Scope:** if implementation needs to touch more than 8 production files or
  more than ~120 net lines of production prose, stop and escalate — this is a
  small doc-and-test normalisation.
- **Behaviour:** if any production change is not confined to a docstring/comment
  (i.e. a code line would change), stop and escalate; the constraint is
  violated.
- **Suite drift:** if normalising a docstring reddens any *behavioural* suite
  (compile, done-predicate, disk-evidence, reconcile, desloppify), stop and
  escalate — it means a docstring was load-bearing in a way the plan did not
  anticipate.
- **Guard brittleness:** the round-2 design already scopes the guard to
  cross-reference presence + the authoritative table markers (no member-count,
  no authority-token scan), per Decision Log "WI3 discriminator". If even this
  cross-reference-first guard cannot pass the `check_compiled`-shaped fixture
  while still reddening a bare re-export spelling, stop and escalate with the
  failing cases — do NOT re-introduce a member-enumeration heuristic, which the
  round-1 review proved unworkable against the heterogeneous consumers.
- **Dependencies:** if any new third-party dependency seems required, stop and
  escalate — none is expected (stdlib + pytest only).
- **Ambiguity:** if the set of "consolidated §7.1 projections" the guard must
  cover is unclear (e.g. whether 7.1.1's `compile_is_current` or 7.1.4's
  finding-outcome skeleton each warrant a guard row), present the options and
  ask before widening scope.

## Risks

    - Risk: a textual drift-guard is brittle — a member-count or
      "authority-token" heuristic false-positives on a legitimate consumer.
      Severity: medium (mitigated to low by the chosen design)
      Likelihood: medium
      Mitigation: RESOLVED in round 2. The guard does NOT count members and
      does NOT parse the prose for an authority token; it keys the
      authoritative symbol by registry position and asserts only
      (a) the authoritative __doc__ carries the table markers, and (b) each
      consumer __doc__ carries the defining-module cross-reference and no bare
      re-export tail. This is the cross-reference-first design audit-7.1.2
      Finding 3 and the Tolerance both prefer, and it survives the real,
      heterogeneous consumer tree (check_compiled names 3 members,
      _check_compiled_matches_drafts names 2, compile_consistent names 0). A
      check_compiled-shaped negative fixture proves no false positive. See
      Decision Log "WI3 discriminator".

    - Risk: a future edit re-expands a consumer's prose into a full table while
      keeping its cross-reference, shipping green.
      Severity: low
      Likelihood: low
      Mitigation: accepted residual under the cross-reference-only design. The
      authoritative table remains the only *cited* source, so the projection
      cannot silently *re-fork* (the §7.1 invariant); the developers'-guide
      convention (WI4) plus code review catch prose bloat. Recorded as the
      explicit trade-off in Decision Log "WI3 discriminator".

    - Risk: normalising _compile.py's docstrings silently changes a doctest or
      a behavioural assertion that greps the text.
      Severity: low
      Likelihood: low
      Mitigation: leta refs / grep for any test asserting against these exact
      strings before editing; run the compile suite after each edit. Verified
      round 2: no doctests (no >>> markers); three TEST docstrings name the
      re-export path (test_compile_check_agreement.py:6,
      test_compiled_matches_drafts.py:3, test_reconciliation_payload.py:3) but
      these are test prose, out of the guard registry, and assert nothing
      against the production spelling — the safety greps EXPECT them.

    - Risk: 7.1.5 lands after 7.1.6 and re-spells a cross-reference via the
      re-export path, re-opening the inconsistency the guard is meant to close.
      Severity: low
      Likelihood: medium
      Mitigation: the guard is authored generically over a registry of
      (defining-symbol, consumer-symbols) rows; document in the developers'
      guide and the guard's own docstring that 7.1.5 (and any later §7.1 task)
      must add its row when it consolidates a projection. The guard's failure on
      a missing/re-export reference is the enforcement.

    - Risk: the re-export path is genuinely needed somewhere (e.g. a public-API
      docstring deliberately points readers at the stable façade).
      Severity: low
      Likelihood: low
      Mitigation: the §7.1 consumers in scope are internal command/state
      modules, not public-API surface; the audit explicitly calls the
      defining-module path canonical for these. If a deliberate façade reference
      is found, record it in the Decision Log as an out-of-scope carve-out and
      exclude it from the guard rather than rewriting it.

## Progress

    - [x] Work item 1: normalise compile-projection cross-references to the
      defining-module path in commands/_compile.py (eight refs) and in
      state/compile_model.py::compile_is_current (one intra-module relative ref).
      DONE 2026-06-27: all eight `_compile.py` refs (lines 12, 14, 34, 104, 106,
      175, 181, 186) and `compile_is_current` line 106 rewritten to the
      defining-module path; post-edit grep shows zero re-export spellings in
      `novel_ralph_skill/`; `compile_is_current.__doc__` now carries the canonical
      path; `make all` green (1396 passed, 1 skipped); diff is docstring-only.
    - [x] Work item 2: normalise the reconciliation-payload cross-reference in
      commands/novel_state.py to the defining-module path.
      DONE 2026-06-27: `_render_reconciliation` line 136 rewritten to
      `novel_ralph_skill.state.reconcile.reconciliation_payload`. Confirmed
      `_reconcile.py` carries NO `:func:` cross-reference to the payload (only an
      import line 62 and direct calls 223/242/284), so no edit there (see Surprises
      "WI2 — _reconcile carries no payload cross-reference"). Post-edit grep shows
      zero re-export spellings in `novel_ralph_skill/`; `make all` green.
    - [x] Work item 3: add the reusable projection-docstring drift-guard
      (red-first) and wire the two consolidated projections through it.
      DONE 2026-06-27: added `tests/test_projection_docstring_drift_guard.py` (one
      file, under the 400-line cap, no sibling scanner needed). The helper
      `assert_single_authoritative_projection(row)` makes the three independent
      assertions (authoritative table markers; consumer canonical path present;
      consumer re-export tail absent) keyed by registry position. Registry binds
      the two projections (compiled_matches_drafts → 4 consumers;
      reconciliation_payload → 1 consumer) via live imports. Negative fixtures
      cover: omitted cross-reference (assertion 2), bare-re-export-only spelling
      (assertion 2), CO-LOCATED canonical+tail (assertion 3, the non-vacuous
      tail-branch proof for B3-1), bare-relative role (assertion 2), and hollowed
      authoritative (assertion 1). Positive fixtures: canonical-only consumer and
      a check_compiled-shaped three-member consumer (no false positive). 9 tests
      pass; `make all` green at 1405 passed. Red-before demonstrated (transcript in
      Artifacts).
    - [x] Work item 4: document the convention and guard in the developers'
      guide so 7.1.5 (and later §7.1 tasks) inherit it.
      DONE 2026-06-27: added the subsection "The authoritative-docstring +
      consumer self-projection convention (roadmap §7.1)" under the
      "One owner for …" material in `docs/developers-guide.md` (§"Done predicate"),
      recording the single-authoritative-docstring rule, the canonical
      defining-module-path rule (including the intra-module / bare-relative case),
      and the reusable drift-guard with how a new §7.1 task registers a row. en-GB
      Oxford-spelled, no Mermaid. `make markdownlint` (file lints clean),
      `make nixie`, and `make all` all green.

## Surprises & discoveries

    - Observation: the worktree arrived with a large pre-existing dirty tree —
      most of `docs/` and `skill/` showed as modified at session start, unrelated
      to this task.
      Evidence: `git status --short` at session start listed ~270 ` M` docs/skill
      files before any edit; `git --no-pager diff --stat` shows them as
      reflow/churn, not 7.1.6 content.
      Impact: each work item is committed by staging ONLY its own files
      (`git add <specific paths>`), never `git add -A`, so the inherited churn is
      excluded from every 7.1.6 commit. The execplan itself
      (`docs/execplans/roadmap-7-1-6.md`) is staged with its work item because it
      is this task's living document.

    - Observation: WI1 coderabbit flagged two minor issues, both in the execplan
      itself, not in production: a second-person "you" sentence in the context
      section and a "confirm a clean tree" step that only checked the branch name.
      Evidence: `/tmp/cr_wi1.log` — two `minor` findings on
      `docs/execplans/roadmap-7-1-6.md` lines 559-563 and 999-1002.
      Impact: both fixed in WI1 — the context paragraph now opens "Work in the git
      worktree…" and the pre-flight step adds `git status --porcelain`. No
      production change resulted.

    - Observation: `make markdownlint` is RED in this worktree, but every failing
      file is inherited churn or an untracked planning artifact — none is a file
      this task commits.
      Evidence: `markdownlint-cli2 '**/*.md'` fails on ~74 files; every one is
      either dirty-vs-HEAD inherited churn (e.g. `docs/issues/audit-7.1.2.md`,
      whose COMMITTED HEAD version lints clean) or an untracked
      `roadmap-7-1-6.logisphere-review-r{1,2}.md` planning artifact. The task's own
      execplan `docs/execplans/roadmap-7-1-6.md` lints clean (0 errors), as does
      every file 7.1.6 commits. `make all` (build, check-fmt, lint, typecheck,
      test) — which does NOT include markdownlint — is green.
      Impact: out of scope to fix here (it would require editing ~270 files this
      task does not own, violating the standing "never read-modify-write inherited
      files" rule). The df12-build workflow parks this detritus at merge time (the
      stash list shows "park stale … cleanup detritus" operations). Recorded as an
      open issue; not a regression introduced by 7.1.6.

    - Observation: WI2 — `_reconcile.py` carries NO `:func:` cross-reference to
      `reconciliation_payload`, so it is correctly NOT a guard consumer row and
      WI2 made no edit there.
      Evidence: `grep -n 'reconciliation_payload' _reconcile.py` →
      import (line 62) and direct calls (223, 242, 284) only;
      `grep -nE ':func:`[^`]*reconciliation_payload' _reconcile.py` → no hits.
      Impact: the only payload consumer carrying a `:func:` cross-reference is
      `novel_state._render_reconciliation` (line 136), confirming the round-3
      registry-coverage decision. No deviation from the plan.

    - Observation: WI3 — ruff/pylint forced three mechanical adjustments to the
      new guard module; none changed the guard's logic.
      Evidence: ruff flagged TC003 (move `collections.abc` into a TYPE_CHECKING
      block), EM102 (assign the AssertionError message to a local), and PT018
      (split a composite `assert a and b`); pylint flagged R0913 (too-many-arguments
      on the five-keyword helper). Fixed by moving `cabc` under `TYPE_CHECKING`,
      hoisting the message to a local, splitting the co-located fixture assertion
      into two, and refolding the helper to take a single `ProjectionRow` argument
      (with a `_row(...)` builder for the synthetic unit fixtures).
      Impact: the helper signature is now `assert_single_authoritative_projection(
      row: ProjectionRow)`; the three assertions and the red-before/green-after
      behaviour are unchanged. `make all` green at 1405 passed.

## Decision log

    - Decision: cuprum and the firecrawl external-library research are out of
      scope for this task.
      Rationale: 7.1.6 is doc-and-test only. The drift-guard reads docstrings
      in process via imported __doc__, mirroring
      tests/test_developers_guide_contract_drift_guard.py and
      tests/test_skill_contract_drift_guard.py, which explicitly state "no
      subprocess". cuprum appears only in the e2e suites that drive the
      installed console scripts (verified: grep "cuprum" hits only tests/*_e2e
      and command-surface/installed-binary fixtures, never the unit guards). No
      Cyclopts, pytest-timeout, or uv-run behaviour is exercised by a new
      in-process docstring assertion. There is therefore no external-library
      behaviour to pin; the no-subprocess constraint is the justified scoped
      alternative.
      Date/Author: 2026-06-27, planning agent

    - Decision: the guard lives in a new module
      tests/test_projection_docstring_drift_guard.py with parsing logic kept
      pure and importable, splitting into a sibling helper only if the 400-line
      cap is approached.
      Rationale: mirrors the established repository prose-guard pattern
      (test_skill_contract_drift_guard.py + _skill_contract_scanner.py,
      test_developers_guide_contract_drift_guard.py). A new dedicated module
      keeps the docstring invariant colocated and discoverable, and keeps
      test_compile_model_seam.py focused on behaviour (its docstring already
      says it pins the seam behaviour, not the prose).
      Date/Author: 2026-06-27, planning agent

    - Decision: 7.1.6 does not hard-depend on 7.1.5; the guard covers only the
      two projections whose consumers carry re-export/mixed spelling today
      (compile-currency / absent-file table via compiled_matches_drafts, and the
      reconciliation payload via reconciliation_payload).
      Rationale: roadmap 7.1.6 Requires 7.1.2, 7.1.3, 7.1.4 (NOT 7.1.5);
      7.1.5 is still "[ ]" on main. The roadmap body asks to "apply the
      convention and guard to the remaining §7.1 task (7.1.5) so each inherits
      the convention rather than re-deciding it" — that is satisfied by
      documenting the convention and authoring the guard as an extensible
      registry, so 7.1.5 adds its row when it lands. The guard must not import
      ENVELOPE_FIELD_ORDER or any 7.1.5-only symbol.
      Date/Author: 2026-06-27, planning agent

    - Decision (WI3 discriminator): commit to a **cross-reference-first,
      registry-keyed** guard. Drop the member-enumeration / "names all three
      members with both polarities" heuristic entirely. The guard asserts, per
      registry row: (a) the *authoritative* symbol (the row key) carries the
      full-projection table markers in its __doc__; (b) each *consumer* symbol
      carries the **defining-module** cross-reference substring in its __doc__
      and carries NO bare re-export tail; the authoritative-vs-consumer
      distinction is by registry position, not by any prose token.
      Rationale: round-1 review B2 + Wafflecat's open question proved the
      member-count heuristic reds a registered consumer. Verified against the
      real tree (grep evidence in §"Source verification, round 3"):
      check_compiled names all three CompiledComparison members AND both
      absent-file polarities (lines 181-188), so no member-count threshold
      separates it from the authoritative table; and the phrases "single
      production site"/"single source"/"authoritative … table" all occur inside
      consumer docstrings as references to the canonical site
      (check_compiled __doc__ line 174; _check_compiled_matches_drafts __doc__
      line 196; compile_consistent __doc__ line 234), so no free-floating token
      discriminates either. Registry position is therefore the only robust
      key — exactly how tests/test_developers_guide_contract_drift_guard.py keys
      the authoritative field set off the imported Envelope dataclass, not off a
      parsed token. Trade-off accepted: a consumer could re-expand its prose
      without dropping its cross-reference and ship green; the authoritative
      table stays the only *cited* source, so the projection cannot silently
      re-fork (the §7.1 invariant the task protects), and WI4's documented
      convention plus review catch prose bloat. A check_compiled-shaped negative
      fixture (a string naming all three members + both polarities + a correct
      defining-module cross-reference) is added to PROVE the guard passes it
      (no false positive); the negative fixtures that must RED are a missing
      cross-reference and a bare re-export-path spelling.
      Date/Author: 2026-06-27, planning agent (round 2)

    - Decision (registry coverage): the guard registry carries one row per
      *authoritative projection symbol*, binding it to the consumer symbols that
      cross-reference it. Rows:
      (1) compile_model.compiled_matches_drafts → consumers
          compile_model.compile_is_current (normalised by WI1 — see Decision Log
          "compile_is_current normalisation"), done_predicate.compile_consistent,
          disk_evidence._check_compiled_matches_drafts,
          commands._compile.check_compiled;
      (2) reconcile.reconciliation_payload → consumer
          commands.novel_state._render_reconciliation.
      The concatenate_drafts / present_draft_bodies references WI1 normalises in
      _compile.py (lines 12, 14, 104, 106) are normalised-for-consistency but
      are NOT guarded as their own registry rows in 7.1.6: their authoritative
      home is compile_model and their consumer graph is wider than this task's
      audit scope. This is the explicit coverage boundary the round-1
      Improvement asked for. A future task that consolidates those projections
      adds their rows; 7.1.6 leaves them normalised-but-unguarded by design, not
      by oversight. compile_manuscript is NOT a registry consumer row (it
      cross-references concatenate_drafts/present_draft_bodies, not
      compiled_matches_drafts); its lines 104/106 are covered by WI1's
      normalisation only.
      Date/Author: 2026-06-27, planning agent (round 2)

    - Decision (compile_is_current normalisation — resolves R2-B1): NORMALISE,
      do not drop. compile_model.compile_is_current is a registered consumer of
      the compiled_matches_drafts projection, but its docstring cross-references
      the authoritative table with the BARE RELATIVE spelling
      ``:func:`compiled_matches_drafts``` (compile_model.py line 106), which
      carries neither the canonical defining-module path nor the re-export tail
      (verified round 3: canonical-substring present = False, re-export tail
      present = False). The round-2 plan's "compile_model.py needs no spelling
      change" claim was therefore wrong for this symbol, and the guard's
      consumer-cross-reference assertion would have RED on it on the normalised
      tree. Of the review's two options — (a) normalise the bare relative ref to
      the canonical path and fold it into WI1, or (b) drop compile_is_current
      from the consumer set with a recorded carve-out — round 3 chooses (a). It
      keeps the registry uniform (every compile-family consumer carries the
      canonical path), is the marginally stronger choice the round-2 Alternatives
      checkpoint preferred, and avoids a carve-out the convention text would have
      to special-case. WI1 now rewrites compile_is_current line 106 from
      ``:func:`compiled_matches_drafts``` to
      ``:func:`~novel_ralph_skill.state.compile_model.compiled_matches_drafts```.
      Line 112 (the Parameters note "The three-valued verdict from
      ``:func:`compiled_matches_drafts``") is a parameter-type aside, not the
      authoritative-table cross-reference, and the bare relative form never emits
      the re-export tail, so it may stay relative; normalising only line 106 is
      sufficient and minimal. The negative-fixture set (WI3) adds a
      BARE-RELATIVE case (a docstring whose only projection reference is
      ``:func:`compiled_matches_drafts``` with no dotted path) that the helper
      must RED on the "cross-reference present" assertion, so the chosen rule's
      treatment of intra-module relative refs is pinned, not incidental
      (round-2 R2-B1 fix-required clause). WI4's convention text records that
      intra-module consumers also use the full defining-module path.
      Date/Author: 2026-06-27, planning agent (round 3)

    - Decision (no-bare-re-export check restated — resolves R2-B2): the
      "no bare re-export tail" assertion is the SIMPLE INVARIANT "the bare
      re-export tail substring count is zero in each consumer __doc__", NOT a
      "preceded by"/"equal counts" rule. The round-2 framing rested on a false
      premise: the re-export tail ``state.compiled_matches_drafts`` is NOT a
      substring of the canonical path
      ``novel_ralph_skill.state.compile_model.compiled_matches_drafts`` (the
      canonical contains ``state.compile_model.compiled_matches_drafts``);
      verified round 3 for both projections (tail-in-canonical = False;
      reconcile tail-in-canonical = False). So on the intended green tree the
      tail substring count is 0 while the canonical count is >= 1, and a
      "counts equal" assertion would RED the passing tree while a "preceded by"
      rule would have nothing to match. Round 3 drops that framing entirely. The
      guard's consumer assertion is two INDEPENDENT substring checks: the
      canonical path IS present, and the bare re-export tail is ABSENT (count
      zero). The tail-discriminator unit test must ISOLATE assertion 3 (see
      Decision Log "tail-isolating fixture co-locates both spellings (resolves
      B3-1)" for the round-4 correction): a fixture that names ONLY the bare
      re-export full path (``novel_ralph_skill.state.compiled_matches_drafts``)
      reds on assertion 2 (cross-reference-present), not assertion 3, because it
      lacks the canonical substring; it therefore proves nothing about the tail
      branch. The tail-isolating fixture must co-locate BOTH spellings so
      assertion 2 passes and assertion 3 is the one that raises.
      Date/Author: 2026-06-27, planning agent (round 3; tail-isolation corrected
      round 4)

    - Decision (R2-A2 — table markers are authoritative-only by design): the
      table-marker assertion (compile family: MATCHES/ABSENT/DIVERGES; payload:
      the {action, discrepancies, detail} shape) is asserted ONLY of the
      authoritative symbol, never of consumers, because real consumers
      legitimately name members — check_compiled names all three, compile_is_current
      names all three, _check_compiled_matches_drafts names two — so any
      "markers absent in consumers" rule would RED the green tree. The guard
      module docstring states this explicitly so a later maintainer does not
      "tighten" markers into a consumer check and re-red the suite.
      Date/Author: 2026-06-27, planning agent (round 3)

    - Decision (tail-isolating fixture co-locates both spellings — resolves
      B3-1): the dedicated unit test that proves the "no bare re-export tail"
      check (assertion 3) is NON-VACUOUS must feed the helper a docstring that
      contains the canonical path AND the re-export tail SIMULTANEOUSLY, so
      assertion 2 (cross-reference present) passes and assertion 3 is the one
      that RAISES. The round-3 wording instead fed a docstring whose only
      reference was the bare re-export full path
      ``novel_ralph_skill.state.compiled_matches_drafts``; that string does NOT
      contain the canonical substring
      ``novel_ralph_skill.state.compile_model.compiled_matches_drafts`` (the
      canonical contains the ``.compile_model.`` segment the bare re-export
      lacks), so the helper raises on assertion 2 and never reaches assertion 3.
      The test went red and the suite passed, but it demonstrated the
      cross-reference-present branch, NOT the tail branch — a future edit that
      deleted assertion 3 would keep that test green. Verified constructible
      (§"Source verification, round 4"): a docstring naming both
      ``novel_ralph_skill.state.compile_model.compiled_matches_drafts`` and
      ``novel_ralph_skill.state.compiled_matches_drafts`` has
      ``canonical in doc == True`` and ``tail in doc == True``, so feeding it to
      the helper isolates assertion 3. The plan now specifies TWO distinct
      negative fixtures with distinct red branches: (a) a bare-re-export-ONLY
      fixture that reds on assertion 2 (cross-reference absent), pinning that a
      bare re-export full path is NOT an acceptable cross-reference; and (b) a
      CO-LOCATED fixture (canonical path AND re-export tail together) that reds
      on assertion 3 (no bare re-export tail), proving the tail check fires and
      is non-vacuous. The co-located fixture is deliberately UNLIKE the registry's
      green tree, where the tail is genuinely absent (a green consumer carries
      only the canonical path and has zero tail occurrences); it is a synthetic
      planted string, never a production docstring, exactly so it can exercise the
      tail branch in isolation.
      Date/Author: 2026-06-27, planning agent (round 4)

    - Decision (coderabbit per-work-item handling): WI1's `coderabbit review
      --agent` completed in ~9 min and returned two minor execplan-only findings,
      both fixed in WI1. The WI2 review hung at the "summarizing" phase for ~36 min
      (far past WI1's runtime) and was killed as stalled. Because coderabbit
      reviews the whole branch versus `main` on every run — so a per-commit rerun
      re-reviews the same diff — WI2 (a one-line docstring change identical in form
      to WI1, which coderabbit had already cleared with no production finding) and
      WI4 were committed on the green deterministic gate, and a single combined
      `coderabbit review --agent` was launched after WI4 over the full branch to
      cover the substantive new code (the guard module). That combined run also
      hung at "summarizing" and was killed; the hang reproduces the WI2 stall and
      is an environmental issue with the oversized full-branch diff, recorded in
      Outcomes.
      Rationale: the task allows continuing past a blocked/transient coderabbit run
      (rate-limit / hang) provided the deterministic gates are green and the issue
      is recorded; bundling the trivial WI2/WI4 prose into one final review avoids
      three redundant ~10-min full-branch passes without weakening review coverage
      of the only non-trivial change.
      Date/Author: 2026-06-27, implementation agent

## Outcomes & retrospective

    - COMPLETE 2026-06-27. All four work items landed as atomic commits, each
      gated green with `make all`:
      * WI1 (`Normalise compile-projection cross-refs to the defining-module
        path`): eight `_compile.py` refs + `compile_is_current` line 106
        normalised; zero re-export spellings remain in production.
      * WI2 (`Normalise reconciliation-payload cross-ref to its defining
        module`): `novel_state._render_reconciliation` line 136 normalised;
        `_reconcile.py` confirmed not a consumer row.
      * WI3 (`Add reusable projection-docstring drift-guard`):
        `tests/test_projection_docstring_drift_guard.py` added (9 tests), keyed by
        registry position, with the full negative/positive fixture set including
        the B3-1 co-located tail-isolation fixture. Red-before / green-after
        demonstrated (Artifacts).
      * WI4 (`Document the §7.1 authoritative-docstring + self-projection
        convention`): developers'-guide subsection added.
      No behavioural suite was touched: the compile, done-predicate, disk-evidence,
      reconcile, and desloppify suites stayed green unchanged (1396 → 1405 passed,
      the delta being the new guard's 9 tests). All production hunks are
      docstring-only; no control flow, signature, return value, or exit code
      changed.
      Open issue: `make markdownlint` is red on inherited churn / untracked
      planning artifacts only (see Surprises); every file 7.1.6 commits lints
      clean, and `make all` (which excludes markdownlint) is green at HEAD.
      coderabbit: WI1 returned two minor findings, both in this execplan, both
      fixed. Two subsequent `coderabbit review --agent` runs (the WI2 review and a
      combined post-WI4 review) each hung at the "summarizing" phase for 14-36 min
      — far past WI1's ~9-min runtime — and were killed as stalled. The hang is an
      environmental stall on this branch's oversized full-branch diff (it reviews
      versus `main`, which here carries ~270 files of inherited churn), not a code
      fault. Per the transient-failure guidance, the work is reported done on the
      green deterministic gate with this recorded; WI1's review is the one
      completed pass and it surfaced no production finding.

## Source verification, round 3

Every load-bearing claim below was re-verified against the worktree on
2026-06-27 with the commands shown, so the implementer inherits facts, not a
menu. Round 3 adds the two facts the round-2 review flagged as wrong
(R2-B1 / R2-B2) and pins them.

- **R2-B1 — `compile_is_current` does NOT carry the canonical path; WI1 must
  normalise it.** Importing the live symbol and testing substrings:

        python3 -c "from novel_ralph_skill.state.compile_model import \
          compile_is_current as f; \
          c='novel_ralph_skill.state.compile_model.compiled_matches_drafts'; \
          print('canonical:', c in f.__doc__); \
          print('reexport tail:', 'state.compiled_matches_drafts' in f.__doc__); \
          print('bare relative:', ':func:\`compiled_matches_drafts\`' in f.__doc__)"
        # canonical: False
        # reexport tail: False
        # bare relative: True

  So `compile_is_current` cross-references the table only via the bare relative
  ``:func:`compiled_matches_drafts``` at compile_model.py line 106. WI1
  normalises that single ref to the canonical defining-module path; the round-2
  "compile_model.py needs no spelling change" claim is corrected.
- **R2-B2 — the re-export tail is NOT a substring of the canonical path.**

        python3 -c "c='novel_ralph_skill.state.compile_model.compiled_matches_drafts'; \
          print('tail in canonical:', 'state.compiled_matches_drafts' in c); \
          rc='novel_ralph_skill.state.reconcile.reconciliation_payload'; \
          print('reconcile tail in canonical:', 'state.reconciliation_payload' in rc)"
        # tail in canonical: False
        # reconcile tail in canonical: False

  So the "no bare re-export" check is the simple invariant "tail count == 0",
  not a "preceded by"/"counts equal" rule (Decision Log "no-bare-re-export check
  restated").

## Source verification, round 4

Round 4 pins the single fact the round-3 review flagged as a vacuous test
(B3-1): the tail-isolating fixture must co-locate both spellings. Verified on the
worktree on 2026-06-27 with the command shown.

- **B3-1 — a co-located fixture isolates assertion 3; a bare-re-export-only
  fixture does not.** Constructing both candidate strings and testing the two
  substrings the helper checks:

        python3 -c "c='novel_ralph_skill.state.compile_model.compiled_matches_drafts'; \
          t='state.compiled_matches_drafts'; \
          colocated='See :func:\`~'+c+'\` (re-exported as novel_ralph_skill.'+t+').'; \
          print('co-located canonical:', c in colocated, 'tail:', t in colocated); \
          bare='See novel_ralph_skill.'+t+' for the table.'; \
          print('bare-only canonical:', c in bare, 'tail:', t in bare)"
        # co-located canonical: True tail: True
        # bare-only canonical: False tail: True

  So the CO-LOCATED fixture (canonical present True, tail present True) passes
  assertion 2 and reds on assertion 3 — isolating the tail branch the round-3
  test never reached. The bare-re-export-ONLY fixture (canonical False, tail
  True) reds on assertion 2 instead, which is the *separate* "cross-reference
  absent" negative case, not a tail-branch proof. The same holds for the
  reconciliation projection (canonical
  ``novel_ralph_skill.state.reconcile.reconciliation_payload`` co-located with
  tail ``state.reconciliation_payload`` → both substrings present), but the
  compile-family fixture alone is sufficient to pin the helper's tail branch
  because the helper is projection-agnostic.
- **The three unedited compile-family consumers carry the canonical path (the
  R2-A1 pre-flight gate proves this).** `done_predicate.compile_consistent`
  `__doc__` contains the canonical path twice (lines 224, 234);
  `disk_evidence._check_compiled_matches_drafts` `__doc__` contains it twice
  (lines 197, 209); after WI1, `_compile.check_compiled` contains it (lines
  175, 186). The reconcile authoritative marker `{action, discrepancies,
  detail}` is present in `reconcile.reconciliation_payload.__doc__` (line 160).

- **All eight re-export references in `_compile.py`.** Grepping the re-export
  spellings of `compiled_matches_drafts` / `concatenate_drafts` /
  `present_draft_bodies` / `CompiledComparison` over
  `novel_ralph_skill/commands/_compile.py` returns lines 12, 14, 34, 104, 106,
  175, 181, 186. WI1 normalises all eight.
- **The two consumers already on the defining-module path (guard rows, no
  edit).** Grepping `compile_model.compiled_matches_drafts` over
  `done_predicate.py` → lines 37, 224, 234; over `disk_evidence.py` → lines
  197, 209.
- **`compile_consistent` `__doc__` carries the phrase "authoritative … table".**
  `done_predicate.py` line 234 reads "the authoritative three-valued table" —
  inside the consumer docstring. Confirms an authority *token* cannot
  discriminate authoritative from consumer (Decision Log WI3).
- **`check_compiled` names all three members + both polarities.** `_compile.py`
  lines 181-183 name `MATCHES`/`ABSENT`/`DIVERGES`; lines 184-188 describe both
  absent-file polarities; line 174 reads "from the single production site".
  Confirms B2: no member-count and no authority-token heuristic survives.
- **`_reconcile.py` has NO `:func:` cross-reference to
  `reconciliation_payload`.** Grepping `reconciliation_payload` over
  `novel_ralph_skill/commands/_reconcile.py` → line 62 (import), 223/242/284
  (direct calls) only. So `_reconcile.py` is NOT a registry consumer row and
  WI2 makes no edit there; the only payload consumer carrying a `:func:`
  cross-reference is `novel_state._render_reconciliation` (line 136).
- **`reconciliation_payload` authoritative markers.** `reconcile.py` line 160
  reads "The single source of the ``{action, discrepancies, detail}`` base
  shape". The guard's authoritative table-marker set for this row is the field
  shape `{action, discrepancies, detail}`.
- **No doctests in the edited modules.** Grepping `>>>` over `_compile.py` and
  `novel_state.py` → no hits. Normalising docstrings cannot break a doctest.
- **Three TEST docstrings name re-export paths (out of registry scope; correct
  the B3 narrative).** Grepping the re-export spellings of
  `reconciliation_payload` / `compiled_matches_drafts` over `tests/` (excluding
  the `compile_model.` / `reconcile.` defining paths) →
  `tests/test_compile_check_agreement.py:6`,
  `tests/test_compiled_matches_drafts.py:3`,
  `tests/test_reconciliation_payload.py:3`. These are test-module docstrings,
  not production consumers; the guard registry binds *production* symbols only,
  so they are out of scope and the safety greps EXPECT these hits rather than
  treating them as a surprise.

## Context and orientation

Work in the git worktree at
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-1-6` on branch
`roadmap-7-1-6`. Use `leta` for navigation (`leta show SYMBOL`,
`leta refs SYMBOL`) and `sem` for history; treat `docs/` as source of truth.

Key terms:

- **Projection.** A pure function (or constant) that maps one canonical model
  into a derived shape used by several consumers — for example
  `compiled_matches_drafts` (the three-valued `CompiledComparison` verdict) and
  `reconciliation_payload` (the `Reconciliation` → JSON payload dict).
- **Authoritative docstring.** The single docstring that carries the *full*
  description of a projection (its table / shape / polarities). For the
  compile-currency family this is
  `novel_ralph_skill/state/compile_model.py::compiled_matches_drafts`; for the
  reconciliation payload it is
  `novel_ralph_skill/state/reconcile.py::reconciliation_payload`.
- **Consumer self-projection.** A consumer's docstring describes *only its own*
  polarity in one sentence and cross-references the authoritative docstring
  rather than re-enumerating the whole table.
- **Defining-module path vs re-export path.** `compiled_matches_drafts` is
  *defined* in `novel_ralph_skill.state.compile_model` and *re-exported* from
  `novel_ralph_skill.state` (via `state/__init__.py`). The defining-module path
  (`...state.compile_model.compiled_matches_drafts`) is canonical; the
  re-export path (`...state.compiled_matches_drafts`) is the spelling to remove.
- **Drift-guard.** A test that imports the relevant symbols' `__doc__` and
  asserts the documentation invariant, so a future prose edit that re-forks the
  projection turns the suite red.

Relevant files (full repository-relative paths):

- `novel_ralph_skill/state/compile_model.py` — defines `compiled_matches_drafts`
  (authoritative, lines ~122-191), `compile_is_current` (~90-119),
  `CompiledComparison` (~48). `compiled_matches_drafts` is the authoritative
  anchor the guard pins and needs no spelling change. `compile_is_current`,
  HOWEVER, is a registered consumer and cross-references the table via the
  **bare relative** ``:func:`compiled_matches_drafts``` at line 106, carrying
  neither the canonical path nor the re-export tail (R2-B1, verified §"Source
  verification, round 3"); WI1 normalises that one ref to the canonical
  defining-module path so the consumer satisfies the guard (Decision Log
  "compile_is_current normalisation").
- `novel_ralph_skill/state/done_predicate.py` — `compile_consistent`
  (~213-261) and module docstring (~37) already use the defining-module path
  (`...state.compile_model.compiled_matches_drafts`). In scope only as a guard
  row; no spelling change expected. (Confirm with grep before editing.)
- `novel_ralph_skill/state/disk_evidence.py` —
  `_check_compiled_matches_drafts` (~193-212) and module docstring already use
  the defining-module path. Guard row only; no spelling change expected.
- `novel_ralph_skill/commands/_compile.py` — **the mixed-spelling consumer.**
  Eight re-export references: module docstring lines 12, 14, 34;
  `compile_manuscript` docstring lines 104, 106; `check_compiled` docstring
  lines 175, 181, 186. They name the *re-export* path
  (`novel_ralph_skill.state.compiled_matches_drafts`,
  `...state.concatenate_drafts`, `...state.present_draft_bodies`,
  `...state.CompiledComparison`). Normalise ALL EIGHT to the defining-module
  form. `check_compiled` and the `_compile` module are guard consumer rows for
  the `compiled_matches_drafts` projection; `compile_manuscript`'s lines
  104/106 are normalised-for-consistency only (Decision Log "registry
  coverage").
- `novel_ralph_skill/commands/novel_state.py` — `_render_reconciliation`
  (~130-140) names the *re-export* path
  `novel_ralph_skill.state.reconciliation_payload`; normalise to
  `novel_ralph_skill.state.reconcile.reconciliation_payload`.
- `novel_ralph_skill/commands/_reconcile.py` — uses `derive_reconciliation`
  cross-references; confirm whether its docstrings name
  `reconciliation_payload` (current grep shows only `derive_reconciliation`
  references and direct calls, not a `:func:` to `reconciliation_payload`).
  Treat as a guard consumer row if a cross-reference exists; otherwise no edit.
- `novel_ralph_skill/state/__init__.py` — the re-export façade; unchanged, but
  the reason the re-export path resolves.
- `tests/test_compile_model_seam.py` — pins the seam *behaviour* (truth table);
  the new guard is a *separate* module so this stays behaviour-focused.
- `tests/test_developers_guide_contract_drift_guard.py`,
  `tests/test_skill_contract_drift_guard.py`,
  `tests/_skill_contract_scanner.py` — the prose-guard pattern to mirror
  (in-process, `__doc__`-importing, pure-scanner-in-sibling-module when long).
- `tests/conftest.py` — provides `project_root` and `read_repo_text` fixtures;
  the new guard imports `__doc__` directly, so it needs no markdown reader.
- `docs/developers-guide.md` — where the convention is recorded (work item 4).
- `docs/issues/audit-7.1.2.md` — Findings 2, 3, 5: the source of this task.
- `docs/novel-ralph-harness-design.md` §4.3 (compiled-matches-drafts / draft
  concatenation) and §5.4 (disk-evidence detectors / reconciliation) — the
  design the projections implement; cited by every §7.1 consumer docstring.

Before editing, load skills: `python-router` (it routes to `python-testing` for
the guard and `en-gb-oxendict` for prose). The drift-guard is *example-based*
(a fixed registry of symbols and their docstrings), so `python-verification`
routes to NO adversary: there is no generated input space and no contract to
falsify, so neither Hypothesis, CrossHair, nor mutmut applies. Record that in
the guard's own docstring (mirroring `test_compile_model_seam.py`'s note that
the closed enumeration needs no adversary).

## Plan of work

Four ordered, independently committable, gate-passable work items. Each is
red-then-green where it adds a test, and doc-only-and-green where it only
normalises prose. Run `make all` (and `make markdownlint` + `make nixie` for
the markdown item) before each commit.

### Work item 1 — Normalise compile-projection cross-references in `_compile.py` and `compile_is_current`

Implements: roadmap 7.1.6 (audit-7.1.2 Finding 2); design §4.3, §5.4; ADR-003
(shared interface contract). Skills: `python-router` → `en-gb-oxendict`; `leta`
for refs.

This work item makes the compile-family consumer set uniform: all eight
re-export-path references in `_compile.py`, AND the one bare relative reference
in `compile_model.compile_is_current` (R2-B1), are normalised to the
defining-module path, so every consumer the WI3 guard binds carries the
canonical cross-reference.

In `novel_ralph_skill/commands/_compile.py`, rewrite **all eight**
re-export-path `:func:`/`:attr:` cross-references to the defining-module path,
leaving prose and control flow untouched (verified line numbers, §"Source
verification, round 3"):

- Module docstring line 12: `~novel_ralph_skill.state.concatenate_drafts` →
  `~novel_ralph_skill.state.compile_model.concatenate_drafts`.
- Module docstring line 14: `~novel_ralph_skill.state.present_draft_bodies` →
  `~novel_ralph_skill.state.compile_model.present_draft_bodies`.
- Module docstring line 34: `~novel_ralph_skill.state.compiled_matches_drafts` →
  `~novel_ralph_skill.state.compile_model.compiled_matches_drafts`.
- `compile_manuscript` line 104:
  `~novel_ralph_skill.state.present_draft_bodies` →
  `~novel_ralph_skill.state.compile_model.present_draft_bodies`.
- `compile_manuscript` line 106:
  `~novel_ralph_skill.state.concatenate_drafts` →
  `~novel_ralph_skill.state.compile_model.concatenate_drafts`.
- `check_compiled` line 175: `~novel_ralph_skill.state.compiled_matches_drafts`
  → `~novel_ralph_skill.state.compile_model.compiled_matches_drafts`.
- `check_compiled` line 181:
  `~novel_ralph_skill.state.CompiledComparison.MATCHES` →
  `~novel_ralph_skill.state.compile_model.CompiledComparison.MATCHES`.
- `check_compiled` line 186: `~novel_ralph_skill.state.compiled_matches_drafts`
  → `~novel_ralph_skill.state.compile_model.compiled_matches_drafts`.

`check_compiled` lines 182-183 carry bare relative `~CompiledComparison.ABSENT`
/ `~CompiledComparison.DIVERGES` refs (no `state.` prefix); these already
resolve and are NOT re-export spellings, so leave them unchanged. The guard
(work item 3) asserts the *presence* of the defining-module path and the
*absence* of the bare re-export tail, neither of which is affected by a
relative ref, so no absolute rewrite is forced. Do not alter `check_compiled`'s
one-sentence self-projection or its `Returns`/`Raises` content.

**Then, in `novel_ralph_skill/state/compile_model.py` (R2-B1):** rewrite the one
intra-module bare relative cross-reference in `compile_is_current`'s docstring
to the canonical defining-module path (verified line, §"Source verification,
round 3"):

- `compile_is_current` line 106:
  ``See :func:`compiled_matches_drafts` for the authoritative three-valued
  table…`` →
  ``See :func:`~novel_ralph_skill.state.compile_model.compiled_matches_drafts`
  for the authoritative three-valued table…``.

Leave `compile_is_current` line 112 (the `Parameters` aside "The three-valued
verdict from the bare relative `compiled_matches_drafts` role) as a relative
ref: it is a parameter-type note, not the authoritative-table cross-reference,
and the bare
relative form never emits the re-export tail, so it satisfies the guard without
change (Decision Log "compile_is_current normalisation"). Do not touch the
authoritative `compiled_matches_drafts` docstring (its table is the single home)
or any other prose in the module.

After editing, re-run the verification grep and confirm **zero**
`novel_ralph_skill.state.<symbol>` re-export spellings remain in
`novel_ralph_skill/` production code (the only surviving hits must be the three
TEST-module docstrings, §"Source verification, round 3"); AND confirm the
canonical path is now present in `compile_is_current.__doc__`:

    python3 -c "from novel_ralph_skill.state.compile_model import \
      compile_is_current as f; \
      c='novel_ralph_skill.state.compile_model.compiled_matches_drafts'; \
      print('compile_is_current canonical present:', c in f.__doc__)"
    # expect: compile_is_current canonical present: True

    RX='novel_ralph_skill\.state\.(compiled_matches_drafts'
    RX="$RX"'|concatenate_drafts|present_draft_bodies|CompiledComparison)\b'
    grep -rnE "$RX" novel_ralph_skill/
    # expect: NO hits

Pre-edit safety: grep the four re-export spellings across `novel_ralph_skill/`
and `tests/` to map every occurrence (production hits = the eight lines above;
test hits = the three test docstrings, expected and out of scope); and grep
`>>>` in `_compile.py` to confirm no doctest. The exact commands are in the
`Concrete steps` section.

Tests this item touches: none new yet (the guard arrives in work item 3). The
existing compile suite (`tests/test_compile_check_agreement.py`,
`tests/test_compiled_matches_drafts.py`, the compile e2e) must stay green
unchanged — they assert behaviour, not docstring spelling. Validation:
`make all`.

### Work item 2 — Normalise the reconciliation-payload cross-reference in `novel_state.py`

Implements: roadmap 7.1.6 (audit-7.1.2 Finding 2, extended to the 7.1.3
reconciliation projection per Finding 5); design §5.4; ADR-003. Skills as above.

In `novel_ralph_skill/commands/novel_state.py`, `_render_reconciliation`
docstring (line ~136): rewrite
`~novel_ralph_skill.state.reconciliation_payload` →
`~novel_ralph_skill.state.reconcile.reconciliation_payload`. Leave the call site
(`return reconciliation_payload(reconciliation)`) and prose otherwise
untouched.

Check `novel_ralph_skill/commands/_reconcile.py`: grep confirms its docstrings
cross-reference `~novel_ralph_skill.state.derive_reconciliation` (the
classifier, out of scope here) and call `reconciliation_payload` directly
without a `:func:` cross-reference to it. If a `:func:`…reconciliation_payload
`` cross-reference is found on a closer read, normalise it to the
defining-module path too; otherwise no edit. Record the finding in
`Surprises & Discoveries` either way.

Pre-edit safety:
`grep -rn "state.reconciliation_payload" novel_ralph_skill/ tests/` to confirm
nothing asserts the re-export spelling.

Tests: none new; the reconcile suite (`tests/test_reconcile*`, the reconcile
e2e) stays green unchanged. Validation: `make all`.

### Work item 3 — Add the reusable projection-docstring drift-guard (red-first)

Implements: roadmap 7.1.6 (audit-7.1.2 Finding 3, the drift-guard; Finding 5,
"a reusable drift-guard helper"). Design §4.3, §5.4; ADR-003. Skills:
`python-router` → `python-testing` (fixtures, parametrization);
`python-verification` confirms NO adversary applies (record this); mirror
`tests/test_developers_guide_contract_drift_guard.py` and
`tests/test_skill_contract_drift_guard.py`.

**Discriminator (cross-reference-first, registry-keyed; settled round 2,
corrected round 3).** The guard distinguishes the authoritative docstring from
consumers by REGISTRY POSITION (the authoritative symbol is the row's key),
never by counting members or scanning for an authority token. This is forced by
the real tree and recorded in Decision Log "WI3 discriminator": `check_compiled`
names all three members and both polarities, and the phrases "single production
site"/"authoritative … table" appear inside consumer docstrings, so neither a
member-count nor a token heuristic can tell authoritative from consumer. The
member-enumeration check is DROPPED. The guard mirrors how
`test_developers_guide_contract_drift_guard.py` keys the field set off the
imported `Envelope` dataclass — by symbol identity, not parsed prose.

Round 3 corrects two specifics of the round-2 draft (see Decision Log
"compile_is_current normalisation" and "no-bare-re-export check restated"):
(a) `compile_model.compile_is_current` is a registered consumer whose
pre-normalisation docstring carried only the bare relative
``:func:`compiled_matches_drafts``` — WI1 normalises it to the canonical path so
the "cross-reference present" assertion passes; and (b) the "no bare re-export"
assertion is the simple "tail substring count is zero" invariant, NOT a
"preceded by"/"counts equal" rule, because the re-export tail is not a substring
of the canonical path. The table-marker assertion is authoritative-only (R2-A2),
stated in the guard module docstring, because consumers legitimately name
members.

Create `tests/test_projection_docstring_drift_guard.py` (and, only if it would
exceed ~250 lines, factor the pure parsing into a sibling
`tests/_projection_docstring_scanner.py` exactly as
`tests/_skill_contract_scanner.py` does). The module:

1. Declares a small data structure — one row per consolidated §7.1 projection —
   binding the *authoritative symbol* (the row key) to its *consumer symbols*,
   its *defining-module canonical path*, its *re-export tail*, and its
   *table-marker set* (per Decision Log "registry coverage"):

   - Authoritative: `compile_model.compiled_matches_drafts`. Consumers:
     `compile_model.compile_is_current`,
     `done_predicate.compile_consistent`,
     `disk_evidence._check_compiled_matches_drafts`,
     `commands._compile.check_compiled`. Canonical path:
     `novel_ralph_skill.state.compile_model.compiled_matches_drafts`.
     Re-export tail: `state.compiled_matches_drafts`. Table markers: the three
     member names `MATCHES`/`ABSENT`/`DIVERGES` present in the authoritative
     `__doc__` (asserted only of the authoritative symbol, never of consumers).
   - Authoritative: `reconcile.reconciliation_payload`. Consumer:
     `commands.novel_state._render_reconciliation`. Canonical path:
     `novel_ralph_skill.state.reconcile.reconciliation_payload`. Re-export tail:
     `state.reconciliation_payload`. Table marker: the field shape
     `{action, discrepancies, detail}`.

   `_reconcile.py` is NOT a consumer row: it calls `reconciliation_payload`
   directly with no `:func:` cross-reference (verified, §"Source
   verification"). Bind by importing the live objects so the path is resolved
   by the import system, not a string the guard could mis-key. Do NOT import
   any 7.1.5-only symbol (Constraint).

2. Defines a reusable helper (e.g. `assert_single_authoritative_projection`)
   that, for a row, asserts EXACTLY three things — no member-count, no token
   scan:

   - **(authoritative)** the *authoritative* `__doc__` (the row key) contains
     every table marker for that row (compile family: all three member names;
     payload: the `{action, discrepancies, detail}` field shape). This pins the
     full table to its one home; it is asserted ONLY of the authoritative
     symbol, so a heterogeneous consumer that happens to mention members never
     trips it.
   - **(consumer cross-reference present)** each *consumer* `__doc__` contains
     the canonical defining-module dotted path as a substring (e.g.
     `novel_ralph_skill.state.compile_model.compiled_matches_drafts`). This is
     the load-bearing single-canonical-path assertion.
   - **(consumer no bare re-export)** each *consumer* `__doc__` carries no bare
     re-export spelling — i.e. the re-export tail substring count is **zero**
     (R2-B2). This is a single independent substring check:
     `reexport_tail not in consumer.__doc__`, where `reexport_tail` is
     `state.compiled_matches_drafts` (resp. `state.reconciliation_payload`).
     Do NOT implement a "preceded by `compile_model.`" or "count of tail equals
     count of canonical" rule: the tail is **not** a substring of the canonical
     path (the canonical contains `state.compile_model.compiled_matches_drafts`,
     verified §"Source verification, round 3"), so on the green tree the tail
     count is 0 while the canonical count is >= 1 — a counts-equal assertion
     would RED the passing tree and a "preceded by" rule would have nothing to
     match. The "no bare re-export" check and the "(consumer cross-reference
     present)" check above are two separate, independent assertions, not derived
     from one another. Pin this tail-discriminator with its own unit assertion (a
     dedicated test that does not touch the registry) that ISOLATES assertion 3
     (resolves B3-1; see Decision Log "tail-isolating fixture co-locates both
     spellings"): feed the helper a CO-LOCATED docstring that contains the
     canonical path AND the bare re-export tail simultaneously
     (e.g. one naming both
     ``novel_ralph_skill.state.compile_model.compiled_matches_drafts`` and
     ``novel_ralph_skill.state.compiled_matches_drafts``) and assert it RAISES on
     the tail assertion — assertion 2 (cross-reference present) is satisfied by
     the canonical substring, so the only branch that can red is assertion 3,
     proving the tail check fires. Then feed a docstring containing ONLY the
     canonical path (no tail) and assert it PASSES, proving a green consumer
     genuinely has zero tail occurrences. Do NOT use a bare-re-export-only
     docstring for THIS test: it lacks the canonical substring, so it reds on
     assertion 2 and never exercises the tail branch (that bare-re-export-only
     string is the SEPARATE "cross-reference absent" negative fixture below, with
     a different red branch).

3. Parametrizes over the registry so each projection row is an independent
   test case with a readable id.

**Negative fixtures (prove the discriminator, including no false positive on a
real consumer).** Add parametrized *negative* cases that feed planted docstring
strings through the helper:

- a docstring that OMITS the cross-reference → helper RAISES (cross-reference
     absent, assertion 2);
- a docstring that names ONLY the bare re-export path
     `novel_ralph_skill.state.compiled_matches_drafts` (no `.compile_model.`) →
     helper RAISES on the **cross-reference-present** assertion (assertion 2),
     because that string lacks the canonical substring. This pins that a bare
     re-export full path is NOT an acceptable cross-reference; it does NOT prove
     the tail branch (the next fixture does);
- **a CO-LOCATED docstring** (resolves B3-1) — naming BOTH the canonical path
     `novel_ralph_skill.state.compile_model.compiled_matches_drafts` AND the bare
     re-export full path `novel_ralph_skill.state.compiled_matches_drafts`
     simultaneously → helper RAISES on the **no-bare-re-export** assertion
     (assertion 3): assertion 2 is satisfied by the canonical substring, so the
     only branch that can red is the tail check, proving it fires and is
     non-vacuous. Verified constructible (canonical present True, tail present
     True; §"Source verification, round 4"). This fixture is a synthetic planted
     string, deliberately UNLIKE the registry's green tree where the tail is
     genuinely absent;
- a docstring containing ONLY the canonical path (no tail) → helper PASSES,
     confirming a green consumer carries zero tail occurrences (the positive half
     of the tail-isolation pair);
- **a BARE-RELATIVE docstring** (R2-B1) — whose only projection reference is the
     intra-module relative `:func:` role naming `compiled_matches_drafts` with no
     dotted path, mirroring `compile_is_current`'s *pre-normalisation* shape →
     helper
     RAISES on the "cross-reference present" assertion (the canonical path is
     absent). This pins the chosen rule's treatment of intra-module relative
     refs: a bare relative reference is NOT an acceptable cross-reference, so a
     future §7.1 consumer that uses one is caught rather than silently admitted;
- **a `check_compiled`-SHAPED docstring** — names all three members
     (`MATCHES`, `ABSENT`, `DIVERGES`), describes both absent-file polarities,
     AND carries the correct defining-module cross-reference → helper PASSES.
     This is the regression-proof against B2: a legitimate three-member consumer
     must NOT red. Build the fixture from `check_compiled`'s real docstring shape
     (members + both polarities + cross-reference) so it tracks the actual tree.
- an authoritative-shaped docstring that has been HOLLOWED (table markers
     removed) → the authoritative-marker assertion RAISES.

Red-first discipline (red-before / green-after): the negative fixtures pin the
guard's discriminating power without mutating production code, mirroring how
the developers'-guide guard pins its column/keyword tolerance with explicit
cases. Run the negative cases (they pass — the helper raises on the drift
shapes and passes the check_compiled-shaped case) and the positive registry
cases against the *normalised* tree from work items 1-2 (they pass). To prove
the guard would have caught the pre-normalisation state, temporarily revert one
`_compile.py` reference to the re-export spelling, run the guard, observe the
`compiled_matches_drafts` row go red on the "no bare re-export" assertion, then
restore — record the transcript in `Artifacts and notes`.

Mirror the existing guards' structural choices: in-process, import `__doc__`,
no subprocess, pure scanner colocated, under the 400-line cap. Add the module
docstring note that `python-verification` selects no adversary (closed,
example-based registry; no generated input space), echoing
`test_compile_model_seam.py`.

Validation: `make all`. Acceptance: the positive registry cases pass on the
normalised tree; the negative cases prove the helper raises on a missing
cross-reference (assertion 2), on a bare-re-export-ONLY spelling (assertion 2,
cross-reference absent), on a CO-LOCATED canonical+tail spelling (assertion 3,
the non-vacuous tail-branch proof for B3-1), and on a hollowed authoritative
docstring (authoritative-marker assertion), AND passes both the canonical-only
docstring (tail-isolation positive half) and the `check_compiled`-shaped
three-member consumer fixture (no false positive); reverting any consumer
reference to the re-export path reddens the matching row (demonstrated
transcript).

### Work item 4 — Document the convention so 7.1.5 (and later §7.1 tasks) inherit it

Implements: roadmap 7.1.6 ("apply the convention and guard to the remaining
§7.1 task (7.1.5) so each inherits the convention rather than re-deciding it";
audit-7.1.2 Finding 5). AGENTS.md "Documentation maintenance" (record
conventions in the developers' guide); design §4.3, §5.4. Skills:
`python-router` → `en-gb-oxendict`; documentation-style-guide.

In `docs/developers-guide.md`, add a short subsection under the existing
single-source / drift-guard material (find the section that already documents
the prose-guard pattern via `leta`/grep for "drift-guard" / "single source of
truth") recording:

- the **canonical cross-reference convention**: every consumer of a consolidated
  §7.1 projection names its authoritative target via the *defining-module*
  dotted path, never the `state` re-export façade — and this holds even for an
  *intra-module* consumer (e.g. `compile_is_current`, which sits in the same
  module as `compiled_matches_drafts`): use the full defining-module path, not a
  bare relative ``:func:`name``` (R2-B1; pre-mortem #3). The guard rejects a bare
  relative reference, so a future §7.1 consumer that uses one is caught rather
  than silently admitted;
- the **single-authoritative-docstring invariant**: exactly one docstring holds
  the full projection table; consumers carry a one-sentence self-projection
  plus the cross-reference;
- the **reusable drift-guard**: where it lives
  (`tests/test_projection_docstring_drift_guard.py`), how a new §7.1 projection
  registers a row, and that 7.1.5 (envelope field-order) must add its row when
  it lands rather than re-deciding the convention.

Keep the prose en-GB Oxford-spelled; do not introduce Mermaid (so `nixie` is a
no-op but must still pass). Validation: `make markdownlint`, `make nixie`, then
`make all`.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-1-6`.

1. Confirm branch and a clean tree:

        git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-1-6 branch --show-current
        git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-1-6 status --porcelain
        # expect: roadmap-7-1-6
        # expect: no output (clean tree)

2. Pre-edit safety greps (work items 1-2):

        RX='novel_ralph_skill\.state\.(compiled_matches_drafts'
        RX="$RX"'|concatenate_drafts|present_draft_bodies|CompiledComparison)\b'
        grep -rnE "$RX" novel_ralph_skill/ tests/
        grep -rn 'novel_ralph_skill\.state\.reconciliation_payload' \
          novel_ralph_skill/ tests/
        grep -rn '>>>' \
          novel_ralph_skill/commands/_compile.py \
          novel_ralph_skill/commands/novel_state.py
        # expect (verified round 3):
        #   production: _compile.py lines 12,14,34,104,106,175,181,186;
        #               novel_state.py line 136.
        #   tests (out of scope, EXPECTED): test_compile_check_agreement.py:6,
        #               test_compiled_matches_drafts.py:3,
        #               test_reconciliation_payload.py:3.
        #   no ">>>" doctest lines.

   R2-A1 pre-flight GATE — prove the three unedited compile-family consumers and
   the reconcile authoritative symbol carry the canonical markers BEFORE
   authoring the guard, so a missing one fails loudly here, not mid-WI3:

        python3 - <<'PY'
        from novel_ralph_skill.state.done_predicate import compile_consistent
        from novel_ralph_skill.state.disk_evidence import (
            _check_compiled_matches_drafts as dcheck,
        )
        from novel_ralph_skill.state.reconcile import reconciliation_payload
        canon = "novel_ralph_skill.state.compile_model.compiled_matches_drafts"
        assert canon in compile_consistent.__doc__, "compile_consistent missing canon"
        assert canon in dcheck.__doc__, "disk_evidence missing canon"
        assert "{action, discrepancies, detail}" in reconciliation_payload.__doc__, \
            "reconcile marker missing"
        print("R2-A1 pre-flight OK")
        PY
        # expect: R2-A1 pre-flight OK

3. Apply work item 1 edits to `novel_ralph_skill/commands/_compile.py` (all
   eight references) AND to `novel_ralph_skill/state/compile_model.py`
   (`compile_is_current` line 106 bare relative ref → canonical, R2-B1), confirm
   zero re-export spellings remain in production AND that `compile_is_current`
   now carries the canonical path, then run the gate:

        RX='novel_ralph_skill\.state\.(compiled_matches_drafts'
        RX="$RX"'|concatenate_drafts|present_draft_bodies|CompiledComparison)\b'
        grep -rnE "$RX" novel_ralph_skill/
        # expect: NO hits
        python3 -c "from novel_ralph_skill.state.compile_model import \
          compile_is_current as f; \
          c='novel_ralph_skill.state.compile_model.compiled_matches_drafts'; \
          assert c in f.__doc__; print('compile_is_current canonical OK')"
        # expect: compile_is_current canonical OK
        make all
        # expect: all gates green; the compile suite unchanged.

   Commit (file-based message; imperative; en-GB):

        Normalise compile-projection cross-refs to the defining-module path

4. Apply work item 2 edit to `novel_ralph_skill/commands/novel_state.py`
   (and `_reconcile.py` if a cross-reference is present), then `make all`, then
   commit:

        Normalise reconciliation-payload cross-ref to its defining module

5. Add work item 3's guard module (red-first via negative cases), then:

        make all
        # expect: the new guard's positive cases pass on the normalised tree;
        # negative cases prove the helper rejects drift.

   Demonstrate catch-power: temporarily revert one `_compile.py` reference to
   the re-export spelling, run the guard, capture the red transcript, restore:

        # edit check_compiled's line-186 ref back to
        #   …state.compiled_matches_drafts (drops .compile_model.)
        .venv/bin/pytest -v tests/test_projection_docstring_drift_guard.py
        # expect: the compiled_matches_drafts row FAILS — the reverted ref both
        #   drops the canonical path on that occurrence AND reintroduces the bare
        #   re-export tail, so the "no bare re-export" assertion reds.
        # restore the edit, re-run: expect PASS

   Commit:

        Add reusable projection-docstring drift-guard

6. Apply work item 4's developers'-guide subsection, then:

        make markdownlint
        make nixie
        make all

   Commit:

        Document the §7.1 authoritative-docstring + self-projection convention

## Validation and acceptance

Run `make all` from the worktree root after every work item; run
`make markdownlint` and `make nixie` after the markdown item. The full gate
(`make all` = build, check-fmt, lint, typecheck, test) must be green at each
commit (AGENTS.md quality gates).

Quality criteria (what "done" means):

- **Tests:** the new `tests/test_projection_docstring_drift_guard.py` passes;
  its positive registry cases assert each consumer carries the defining-module
  cross-reference with no bare re-export tail, and that each authoritative
  docstring carries its table markers; its negative cases prove the helper
  raises on a missing cross-reference (assertion 2), a bare-re-export-only
  spelling (assertion 2), a CO-LOCATED canonical+tail spelling (assertion 3 —
  the non-vacuous tail-branch proof, B3-1), and a hollowed authoritative
  docstring, AND passes both the canonical-only docstring (tail-isolation
  positive half) and a `check_compiled`-shaped three-member consumer fixture
  (no false positive). Reverting any consumer
  reference to the re-export path reddens the matching row (demonstrated
  transcript in `Artifacts and notes`). The compile, done-predicate,
  disk-evidence, reconcile, and desloppify suites stay green unchanged.
- **Lint/typecheck:** `make lint` (Ruff + interrogate 100% docstring coverage +
  Pylint) and `make typecheck` (`ty check`) pass; the new guard module carries
  docstrings to satisfy interrogate.
- **Behaviour:** no production code line changes (only docstrings); confirm with
  `git diff --stat` and a `git diff` review that production hunks are
  docstring-only.
- **Markdown:** `make markdownlint` and `make nixie` pass for the
  developers'-guide change.
- **Spelling:** en-GB Oxford spelling throughout (`en-gb-oxendict`), external
  API identifiers (dotted paths, `:func:` roles) reproduced verbatim.

Quality method (how we check):

- `make all` (+ `make markdownlint`, `make nixie`) per work item; manual
  `git diff` review confirming production hunks are docstring-only; the
  temporary-revert transcript proving the guard's catch-power.

## Idempotence and recovery

Every work item is a docstring/test edit, re-runnable without side effects; no
migrations, no destructive operations. If `make all` fails after an edit,
`git diff` the offending file and revert the single hunk; the guard and the
behavioural suites localise the failure. The temporary-revert demonstration in
step 5 must be undone before committing (verify with `git status` / `git diff`
that the reverted reference is restored). Commit only when the gate is green
(AGENTS.md).

## Artifacts and notes

Captured during implementation:

- Pre-edit grep mapping the re-export spellings: eight production lines in
  `_compile.py` (12, 14, 34, 104, 106, 175, 181, 186) plus one in
  `novel_state.py` (136), and the three out-of-scope TEST-docstring hits
  (`test_compile_check_agreement.py:6`, `test_compiled_matches_drafts.py:3`,
  `test_reconciliation_payload.py:3`) — exactly as the round-3 verification
  predicted.
- Post-WI1 grep over `novel_ralph_skill/` for the four re-export spellings
  returns ZERO hits; post-WI2 grep for `state.reconciliation_payload` likewise
  returns zero production hits. `compile_is_current.__doc__` now carries the
  canonical path (verified by import).
- R2-A1 pre-flight gate printed "R2-A1 pre-flight OK": `compile_consistent` and
  `_check_compiled_matches_drafts` already carry the canonical path, and
  `reconciliation_payload` carries the `{action, discrepancies, detail}` marker.
- Temporary-revert transcript (red-before / green-after). One `check_compiled`
  reference in `_compile.py` was reverted to the bare re-export spelling
  (dropping `.compile_model.`), then the guard was run:

        $ .venv/bin/python -m pytest \
            tests/test_projection_docstring_drift_guard.py::\
            test_projection_is_single_authoritative -v
        …
        E  AssertionError: consumer <function check_compiled …> docstring
        E    carries the bare re-export tail 'state.compiled_matches_drafts';
        E    use the defining-module path instead
        FAILED …::test_projection_is_single_authoritative[compiled_matches_drafts]
        1 failed, 1 passed

  The reverted reference both drops the canonical path on that occurrence AND
  reintroduces the bare re-export tail, so the row reds on the "no bare
  re-export" assertion (assertion 3). The file was then restored from a backup
  and the guard re-run: `9 passed`. Post-restore grep confirms zero re-export
  spellings remain.

## Interfaces and dependencies

No new third-party dependency. Standard library + pytest only.

In `tests/test_projection_docstring_drift_guard.py` (pure helper may move to
`tests/_projection_docstring_scanner.py` if the cap is approached), define a
reusable guard helper with a stable signature, for example:

        def assert_single_authoritative_projection(
            *,
            authoritative: object,  # live symbol owning the full table (row key)
            consumers: cabc.Sequence[object],  # live consumer symbols
            canonical_path: str,  # defining-module dotted path
            reexport_tail: str,  # the bare re-export tail, e.g.
                                 # "state.compiled_matches_drafts"
            table_markers: cabc.Sequence[str],  # asserted ONLY of authoritative
        ) -> None:
            # 1. every table marker present in authoritative.__doc__
            #    (asserted ONLY of the authoritative symbol — R2-A2)
            # 2. canonical_path present in each consumer.__doc__
            #    (a bare relative ":func:`name`" does NOT satisfy this — R2-B1)
            # 3. reexport_tail substring count is ZERO in each consumer.__doc__
            #    (i.e. reexport_tail not in consumer.__doc__ — R2-B2; the tail is
            #    NOT a substring of canonical_path, so a green consumer carrying
            #    only the canonical path genuinely has zero tail occurrences)
            …

The helper makes NO member-count or authority-token assertion; the
authoritative-vs-consumer split is the registry shape (the `authoritative`
argument is the row key), exactly as
`test_developers_guide_contract_drift_guard.py` keys its field set off the
imported `Envelope` dataclass. The registry of rows binds the live symbols
(`novel_ralph_skill.state.compile_model.compiled_matches_drafts` and its four
consumers; `novel_ralph_skill.state.reconcile.reconciliation_payload` and its
single consumer `_render_reconciliation`) and is parametrized so each
projection is an independent case. The helper imports `__doc__` in process — no
subprocess, no cuprum, no Cyclopts, no `uv run`.
