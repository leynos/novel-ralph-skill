# Logisphere design review — roadmap 3.1.4, round 2

Adversarial pre-implementation review of `docs/execplans/roadmap-3-1-4.md`
(anchor unresolved-BLOCKER resolution positionally; cover the false-clean
direction). Round 2 confirms the round-1 blocking point B1 is resolved and the
plan is implementable as written.

Verdict: **Satisfied — proceed to implementation.**

## Round-1 blocker B1 — resolved

The round-1 blocker was that "extend `blocker_edge_trees`" left the fixture's
two destructuring consumers unspecified, so a 3-tuple bump would break
`test_blocker_edges`'s two-element unpack and the type annotations, failing the
W3 `make all` gate. Round 2 closes this:

- The fixture is confirmed at `tests/corpus_done_predicate_fixtures.py:91-115`,
  typed `cabc.Callable[[], tuple[Path, Path]]`, inner `_build` returning the
  two-element `(resolved, near_miss)`. The plan's W3 step 4.1 names the exact
  widening to `tuple[Path, Path, Path]` (annotation, docstring `Returns`, inner
  `_build` annotation) and the third `incidental` sub-build. Matches source.
- `test_blocker_edges` (`tests/test_working_corpus_done_predicate.py:90-97`)
  does `resolved, near_miss = blocker_edge_trees()`. W3 step 4.2 names the
  three-element unpack and the new assertion
  `incidental.failed_clause_names == ("no_unresolved_blockers",)`. The
  incidental tree differs from all-hold only in the note body (via
  `_note_on_first_chapter`), so it does fail on exactly that one clause —
  verified against the all-hold spec and the existing near-miss precedent.
- `test_blocker_oracle_twin_agrees` (`:123-136`) uses
  `cases.extend(blocker_edge_trees())`, which is length-agnostic. W3 step 4.3
  correctly states only the annotation needs updating; the body consumes the
  3-tuple unchanged and now pins the twin equal to production on the incidental
  tree. Verified.

D-BLOCKER-EDGE-ARITY records this with the right rationale (position-keyed
3-tuple over a name-keyed mapping, minimal consumer churn).

## Verified against source (round 2)

- The bug is real and load-bearing: `done_predicate.py:288` is
  `_RESOLVED_TOKEN not in stripped`; the false-clean counter-example is wrongly
  cleared. The proposed fix `not stripped.endswith(_RESOLVED_TOKEN)` is the
  smallest sound change.
- Both existing notes stay correct under `endswith`:
  `RESOLVED_BLOCKER_NOTE = "BLOCKER … [resolved]\n"` ends with the token (stays
  clean); `UNRESOLVED`/`NEAR_MISS` carry no token (stay unresolved).
  (`_done_predicate_specs.py:62,66,70`). The unit test
  `test_resolved_blocker_is_clean` writes `… chapter 2 [resolved]\n` — trailing
  token — so it stays green under the new rule.
- The oracle twin re-spells the substring rule at
  `_done_predicate_oracle.py:64`; W3 step 3 changes it in lockstep. The
  cross-check `test_blocker_oracle_twin_agrees` pins it equal to production.
- `__init__.py` exports the BLOCKER constants/trees (lines 36-48, 78-117); the
  plan's "add the new constant and tree here too" is necessary and named.
- The BDD wiring claim is correct: `single_failer_tree`
  (`novel_done_steps.py:89-98`) keys off `DONE_PREDICATE_FAILERS[clause]`, and
  the incidental tree is deliberately *not* a failer-dict member, so a new
  Given step is required — the plan states this definitively (A3 resolved).
- Roadmap success criteria (`roadmap.md:996-999`) and audit Finding 3
  (`audit-3.1.1.md:110-136`, recommending "require the stripped line to end with
  `[resolved]`" plus a corpus near-miss) match the plan's framing exactly.
- W4 doc targets verify: developers-guide `The BLOCKER format` paragraph
  (`developers-guide.md:566-571`, the "acknowledged brittle … substring"
  wording the plan replaces); design §4.2 impl-status block (`:310+`);
  done-conditions.md `contains_unresolved_blocker` reference (~`:181-185`).
- Snapshot deferral (A4) is sound: the snapshot suite snapshots only
  `phase_is_done` and the stale-compile failers
  (`test_novel_done_snapshots.py:104,124`); the `no_unresolved_blockers` failer
  itself is *not* snapshotted, and the incidental tree shares its envelope
  shape, so the plan correctly makes the snapshot optional.
- `make all = build check-fmt lint typecheck test` (`Makefile:28`); the
  markdown gates `markdownlint`/`nixie` exist (`:108,111`). AGENTS.md line 67
  ("failing test before the fix") and line 151-158 (snapshot guidance) exist as
  cited. The W1-folded-into-W2 red-then-green-in-one-commit path satisfies the
  AGENTS.md rule.

## Design-boundary conformance

- Read-only invariant preserved: in-memory line classification only, no write
  introduced (ADR-001; design §3.3). ✓
- Fault boundary untouched: `try/except FileNotFoundError` unchanged; swapping
  `not in` for `not endswith()` neither swallows nor raises a new fault. ✓
- Clause set, order, `DoneClauses` shape unchanged; only the internal grammar of
  one clause moves. ✓
- Deterministic/judgemental boundary respected: no narrative judgement added;
  the predicate stays a pure string-position test. ✓
- No new dependency. The D-BLOCKER-NO-NETWORK rationale holds: the change runs
  no subprocess, so cuprum / Cyclopts / uv / pytest-timeout-under-xdist
  behaviours are genuinely not load-bearing — confirmed by the absence of
  `subprocess`/`cuprum`/`sh.`/`catalogue` in the touched modules. No
  memory-based locked-library claim is asserted, so nothing requires firecrawl
  citation or a pinning test.
- Line-count cap: `done_predicate.py` is at 344/400 and W2 only swaps one
  expression and rewords prose (no net growth risk); `test_done_predicate.py`
  at 314/400 gains two tests (~30-40 lines) — comfortable headroom. ✓

## Atomicity / ordering / testability

- Four work items, each one atomic commit, ordered W1(folded)→W2→W3→W4, each
  ending in its own gate. ✓
- W2 is the red→green soundness fix; W3 pins it in the corpus + BDD; W4 is
  docs-only. Each is independently revertable via `git revert` of one commit. ✓
- Validation is specified per work item and aggregated in
  "Validation and acceptance" with a human-checkable behavioural assertion. ✓

## Pre-mortem (round 2)

- The round-1 most-likely failure (W3 breaking `test_blocker_edges`'s unpack) is
  now pre-empted by the named consumer edits. No residual high-likelihood
  failure mode remains.
- The round-1 second failure (W2 property flaking on whitespace-only `suffix`)
  is closed by the sentinel-terminated construction and the `[]`
  /newline-excluding alphabet in W2 step 2 (A1 resolved): the false-case line
  `f"BLOCKER {prefix} {_RESOLVED_TOKEN} {suffix}X"` provably does not end with
  the token after `.strip()` regardless of `suffix`.

## Residual advisory (non-blocking)

- The grammar-vs-critic-format mismatch (the real `critic-personas.md` uses
  `## BLOCKER` / `### B1 — label` sections with no `[resolved]` token) remains
  a documented limitation (D-BLOCKER-SCOPE, Surprises & discoveries). This is
  the correct scope call for a low-severity step-task; the structured-marker
  grammar is rightly deferred. No action required this task — flagged so the
  eventual reconciliation task is on record.
