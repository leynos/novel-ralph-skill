# Logisphere design review — roadmap 2.3.5 ExecPlan (round 2)

Verdict: PROCEED. The round-1 blocking points (B1-B4) are genuinely resolved, and
every load-bearing claim in the plan was verified against the real source in this
worktree (and the read-only cuprum checkout). No blocking defects remain.

## Claims verified against source (not the planner's summary)

- D-TOKEN-EQUALITY (the premise the whole fixture matrix rests on): verified
  empirically across multi-chapter joins, leading/trailing/interior whitespace,
  whitespace-only bodies, empty bodies, and whole-file trailing whitespace — every
  case gives `len("\n\n".join(bodies).split()) == sum(len(b.split()))`. The
  round-1 false premise (separator/whitespace divergence) is correctly struck.
- `recount_words` (`wordcount.py:86-133`) returns `sum(by_chapter.values())` and
  never opens `compiled.md` — only `.../chapter-NN/draft.md` (`wordcount.py:75`).
- `_check_compiled_matches_drafts` (`disk_evidence.py:173-191`) compares bytes;
  an absent `compiled.md` trivially passes; mismatch yields
  `COMPILED_MATCHES_DRAFTS`.
- `DRAFT_SEPARATOR = "\n\n"` (`compile_model.py:30`).
- The two surviving live contradictions are exactly as named — `schema.py:237`
  and `skill/novel-ralph/references/state-layout.md:114`. A repo-wide search found
  no third live definition (other hits are legitimate finding-references).
- Corpus variant `compiled-not-concatenation-of-drafts`
  (`_variants.py:189-192`, `compiled="not the real concatenation"`) maps to
  `oracle.COMPILED_MATCHES_DRAFTS`. Its base (`COHERENT_BASELINE` = the drafting
  phase) has coherent `[word_counts]`, so its SOLE violation is
  `compiled-matches-drafts` — case 3's assertion is sound. Its compiled token
  count (4) differs from the drafted sum (~68800), so the "not the compiled token
  count" assertion genuinely holds there.
- Case-2 tree `done_flag_real_draft_undercount`
  (`_reconcile_variants.py:23-55`) keeps `BASE`'s chapters and `compiled=None`
  (the drafting baseline sets `compiled=COMPILED_AUTO if is_complete else None`,
  and drafting is not complete). So `compiled-matches-drafts` does NOT fire and
  the sole violation is `word-counts-match-drafts` → RECOUNT. The plan's "absent
  or coherent compiled.md" claim is correct.
- Case-1 fixture is buildable: `WorkingTreeSpec.compiled` accepts an arbitrary
  string (`_specs.py:157-160,182`) and `_drafting_spec`'s
  `by_chapter_override`/`current_words_override` give the stale table.
- `_drive_check` + `ExitCode.ACTIONABLE_FINDING` + `incoherent_tree` exist exactly
  as the plan drives case 3 (`test_novel_state_check_disk.py:35,53,83-90`).
- Design anchors present: §4.1 "pure aggregation" sentence (~288-290),
  §5.2 invariant 3 (~466), §5.4 v1-scope subsection (534-568).
- cuprum/`sh`/`subprocess` non-use: no such import in any of `wordcount.py`,
  `disk_evidence.py`, `reconcile.py`, `_recount.py`, `_reconcile.py`. D-CUPRUM and
  D-NO-FIRECRAWL are honest: the only library behaviours relied on are stdlib
  `str.split` (verified) and `tomlkit`/`pytest` (already locked and exercised).
  No uncited memory-based claim about Cyclopts, pytest-timeout/xdist, or uv exists
  — the new test is a plain in-process pytest module, so those libraries are not
  load-bearing.
- make targets `all`, `check-fmt`, `lint`, `typecheck`, `test`, `markdownlint`,
  `nixie` all exist.

## Panel notes (non-blocking)

- Pandalump (structure): work items are atomic, ordered, independently
  committable, each ends in a stated gate. The decision-and-reconciliation
  framing is structurally honest — the rule is already implemented, so the plan
  records + pins rather than re-implements. No boundary violation: nothing
  crosses the ADR-001 deterministic/judgemental line.
- Telefono (contracts): no public signature changes; the `compiled-matches-drafts`
  exit-4 contract (ADR-003) is preserved untouched. Docstring/prose edits only.
- Doggylump (failure/ops): the "prove it fails red" step is realizable — editing
  `recount_words` to count `compiled.md` makes case 1 fail (present divergent
  file) and case 2 fail (absent file → 0 or error ≠ drafted sum). Idempotence and
  the temporary-edit-revert discipline are spelled out.
- Buzzy Bee (scaling): N/A — doc + one focused test; no runtime cost surface.
- Wafflecat (alternatives): the alternative (compiled-token `current`) is
  explicitly considered and refuted (breaks §5.2 invariant 3 on a stale compile;
  cannot key `by_chapter`). No stronger viable alternative exists for a
  reconciliation task whose rule is already shipped.
- Dinolump (viability): the regression guard's value is forward-looking (guards
  a future refactor), correctly characterized as a non-tautology via the single
  `recount_words(...)[0]` oracle plus the fail-red demonstration.

## Advisory (improve, not blocking)

1. `test_recount_unit.py`'s `_drafting_spec` helper does not expose a `compiled`
   parameter; case 1 must build the `WorkingTreeSpec` so the `compiled` field is
   set (either extend the local helper or construct the spec directly). The plan
   already says "reuse the corpus/WorkingTreeSpec builders", which covers this,
   but the implementer should not assume the existing `_drafting_spec` signature
   suffices unchanged.
2. The case-2 oracle equality ("equals what `recount` would write on the same
   drafts") is strongest if it asserts against `recount_words(working_dir,
   manifest)[0]` directly rather than re-running the `recount` command, to keep
   the two corpus trees from coupling. The plan already states this preference;
   keep it.
3. state-layout.md:114's illustrative `current = 24300` does not sum its truncated
   `by_chapter = { ... }` line; work item 2 correctly says to fix the definition
   comment only and leave the illustrative number. Keep the `...` ellipsis so no
   false "these sum" implication is introduced.
