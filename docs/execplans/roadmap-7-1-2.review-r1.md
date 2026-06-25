# Logisphere design review — roadmap 7.1.2 ExecPlan (round 1)

Verdict: **Proceed with conditions.** The plan is well grounded: every
load-bearing claim about cuprum, Cyclopts, pytest-timeout/xdist, the rulepack
templates, the error hierarchy, and the exit-code routing was verified against
the real source and holds. The remaining items below are precise conditions,
not a rewrite.

## Verified against source (no defect)

- cuprum 0.1.0 API (`sh.make`, `catalogue.lookup`, `UnknownProgramError`,
  `ExecutionContext(cwd=)`, `run_sync(context=, capture=)`) — matches
  `/data/leynos/Projects/cuprum/cuprum/{catalogue.py,sh.py}`.
- Cyclopts 4.18.0 `pathlib.Path | None = None` keyword — proven in-repo by the
  live `--pack` flag (`_desloppify.py` `build_app._scan`).
- pytest-timeout per-test `@pytest.mark.timeout(180)` superseding the 30s
  default
  under xdist — pinned by the working `tests/test_desloppify_e2e.py` running
  under `make test`'s `-n` xdist invocation; not a memory claim.
- Error/exit routing (`EnvelopeMessagesError`, `StateInputError` → exit 3,
  `RulePackError` caught and mapped to exit-2 `CommandOutcome` locally) —
  matches `_desloppify.py` and `contract/runner.py`.
- `ScannedChapter`/`LineHit`/line-by-line `finditer` no-flags model — matches
  `rulepack/detect.py`; `source_chapters(None)` whole-manuscript sourcing
  exists.

## Conditions (advisory — address before/while implementing)

1. `_coerce` reuse is not a free import. Every helper in `rulepack/_coerce.py`
   (`_where`, `_reject_unknown_keys`, `_require*`) hard-raises `RulePackError`,
   not `LedgerError`. Importing them directly would emit the wrong typed error
   (and the wrong `rule '<id>'` wording), so the WI1 "decide whether to import"
   note resolves to **must add a ledger-local `_coerce`** unless the helpers
   are first refactored to take an error factory — which would touch the
   rulepack path (a Tolerance trip). Record this as the WI1 decision rather
   than leaving it open.

2. WI6 e2e: the `_materialise_working` template overwrites **all three**
   `baseline_tree` drafts (chapters 1, 2, 3) with one identical text. The
   window constraints (`allowed_chapters`, `reserved_for_chapter`) cannot be
   exercised cleanly with three identical drafts. WI6's acceptance only commits
   to a `max_count` over-spend (robust: 3 identical hits over `max_count = 2` →
   exit 4), so this is sound as written — but the plan should state that the
   e2e exercises `max_count` only, and either write per-chapter drafts or leave
   the window checks to the in-process tests (WI3/WI5), so the implementer does
   not reach for a window example the template cannot express.

3. Payload pre-decision vs 7.1.3. WI3 specifies a **full-audit-trail** ledger
   payload (every device's `findings`, including `passed` ones). Roadmap 7.1.3
   is the deliberately-deferred "clean-pass slimming" decision and names
   "7.1.1/7.1.2 emit the chosen shape". 7.1.3 is not a declared dependency of
   7.1.2 and the plan correctly keeps the ledger payload separate from the
   rule-pack `_finding_payload`, so this is not blocking — but the plan should
   note that the ledger payload's full-trail choice may be revisited by 7.1.3
   and that the snapshot (WI5) is the churn-absorbing seam, so a later slim is
   a contained snapshot update, not a contract rework.

## Open question (non-blocking)

- No "must appear" floor. The plan reads every window constraint negatively (a
  hit outside the window is a violation; **zero** hits is silent). A
  `reserved_for_chapter = N` bookend the author forgot entirely passes silently
  — arguably the design's headline failure mode ("a forgotten ration silently
  breaks the book"). The design §6.3 example specifies no floor, so the
  negative reading is design-conformant; flagging only as the highest-value
  future enhancement, to be recorded in the developers' guide (WI7) so the
  limitation is explicit, not accidental.

## Pre-mortem (most likely six-month failures)

1. Author-supplied bare-word pattern over-counts (`\bsternum\b` fires on literal
   sternum uses), so a within-discipline book is flagged or a narrowed pattern
   silently under-counts. The plan already owns this (Risk row + WI5 doc + WI6
   collocational example). Mitigation stands.
2. A window check fires against the wrong chapter. Mitigated by reusing the
   already-tested `ScannedChapter.number` attribution and the WI4 property that
   every `LineHit.chapter` is a scanned chapter number. Mitigation stands.
3. `--ledger` + `--chapter` silently produces a partial (wrong) count. The plan
   makes the combination an exit-2 usage fault, pinned by a test. Mitigation
   stands.

## Strongest alternative (Wafflecat)

Extend the rulepack schema with chapter-aware fields rather than a parallel
`ledger/` package. Rejected correctly: the v1 rule-pack key vocabulary is
closed and strictly enforced (`parse.py` `_RULE_KEYS`/`_PACK_KEYS`), the
detector does not understand chapter windows, and the rule-pack contract is a
frozen Constraint (ADR-003). A schema bump would break the frozen contract and
conflate two detection families. The parallel package is the right structural
bet.
