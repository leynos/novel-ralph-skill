# Logisphere design review — roadmap 3.1.3 ExecPlan (Round 2)

Adversarial pre-implementation review of `docs/execplans/roadmap-3-1-3.md`,
read from disk in full. **Verdict: Proceed (satisfied).** The two Round 1
blocking defects (B1, B2) and both advisories (A1, A2) are now closed in the
plan text. Every line-number, signature, and behaviour claim I re-verified
against the real source is accurate. No new blocking defect was found.

## What was re-verified against source this round

- **Detector** `_check_compiled_matches_drafts` (`disk_evidence.py:167-188`):
  absent→`None`; present-equal→`None`; present-diverge→`Violation`. The
  `Violation.detail` string is byte-exact at `:187` ("compiled.md is not the
  ordered concatenation of the present drafts"). The existence check (`:180`)
  runs *before* the draft read (`:182`), so the plan's absent-first ordering
  claim and A1 fault test are correct. Confirmed.
- **Clause** `compile_consistent_exists` (`done_predicate.py:211-220`):
  existence-only, `(working_dir)`-only signature, assembled at
  `done_predicate.py:292`. Confirmed.
- **Clause call-site sweep is complete.** A repo-wide grep finds the production
  call only at `done_predicate.py:292` and the test import only at
  `test_done_predicate.py:32`, with calls at `:144`, `:147`, `:149`. No other
  production or test site references the function, so the `(state, working_dir)`
  signature change ripples exactly where the plan says and nowhere else. The
  function is not in `state/__init__.__all__` (confirmed `done_predicate` is not
  re-exported), so there is no public-surface ripple.
- **`__all__` alphabetization is achievable.** `state/__init__.py` orders
  `__all__` as UPPER_CASE constants, then capitalized classes, then lowercase
  functions (`:90-146`). `CompiledComparison` inserts among the classes (after
  `ChapterEntry`, before `CriticState`); `compiled_matches_drafts` inserts among
  the functions (after `clear_pending_turn`, before `concatenate_drafts`). The
  `compile_model` re-export block at `:27-31` is the correct insertion point.
- **No name collision.** Neither `compiled_matches_drafts` nor
  `CompiledComparison` exists anywhere in production or tests today; the only
  prior mentions are the roadmap's own success criteria (`roadmap.md:952,959`).
- **Test anchors are exact.** `test_disk_evidence.py:101`
  (`compiled-not-concatenation-of-drafts → COMPILED_MATCHES_DRAFTS`) and the
  twin/join-helper test at `:159-176` exist as cited.
  `test_done_predicate.py:135-149` (present-and-absent, with the explicit
  stale→`True` assertion at `:146-147`) and the `evaluate_done` integration at
  `:196-199` (`failed_clause_names == ("compile_consistent",)`) exist as cited.
- **Corpus oracle** `_oracle_disk._check_compiled_matches_drafts` (`:137-149`):
  `working_dir`-only `bool`, absent→`True`, imports no production helper. The
  plan correctly leaves it untouched (D-TWIN). Its continued agreement is the
  behaviour-preservation cross-check, as claimed.
- **Dev-guide edit targets exist.** The compile-model description (`:316-326`)
  and the existence-only paragraph (`:572-579`) are real and accurately
  summarized by WI4.
- **D-NO-CUPRUM is sound.** The diff touches only internal pure-Python modules
  (`compile_model.py`, `disk_evidence.py`, `done_predicate.py`,
  `state/__init__.py`) and pytest suites. There is no subprocess, allowlist,
  `uv run`, Cyclopts, or pytest-timeout surface in the change, so no
  external-library behaviour is load-bearing and none is owed a firecrawl
  citation. Asserting one would be fabrication; the plan correctly declines.

## Round 1 closure check

- **B1 (`make all` does not run `pip-audit`)** — closed. The Surprises section,
  D-RECIPE, "Concrete steps" §3, and "Validation and acceptance" all now state
  `make all = build check-fmt lint typecheck test` (`Makefile:28`) and that
  `pip-audit` lives solely in the separate `audit` target (`:104-105`), not
  load-bearing here.
- **B2 (`make test PYTEST_ADDOPTS=…` not a defined hook)** — closed. The plan
  now directs targeted runs to `uv run pytest <file>` and explicitly notes
  `make test` is `pytest -v -n $(PYTEST_XDIST_WORKERS)` with no file-selection
  parameter (`Makefile:115-116`, `:14`), reserving `make test`/`make all` for
  the full gate.
- **A1 (absent-first fault ordering test)** — closed. WI1 adds the
  undecodable-draft-beside-absent-`compiled.md`→`ABSENT` (no raise) case paired
  with the present-`compiled.md`→raise case, locking the ordering.
- **A2 (name the import line for the clause signature change)** — closed. WI3
  names `test_done_predicate.py:32` and the three calls explicitly.

## Panel pass (Round 2)

- **Pandalump (structure):** boundaries hold. `compile_model` is the lowest
  module; both consumers depend downward only; no import cycle (confirmed R1,
  unchanged). CQS / ADR-001 read-only boundary preserved — the helper is a pure
  `(State, Path) -> CompiledComparison` query.
- **Wafflecat (alternatives):** the `enum` over the audit's literal `bool` is
  the correct deviation (a `bool` collapses absent and diverges, which the
  detector must distinguish); justified in D-SHAPE and gated by Tolerance
  "Ambiguity". The only surviving alternative — a `Literal[...]` string — trades
  exhaustiveness checking for one fewer symbol; not worth reopening.
- **Buzzy Bee (scaling):** none — pure refactor over identical disk reads.
- **Telefono (contracts):** public surface grows by exactly two symbols on
  `compile_model`; the only changed signature is the non-exported clause gaining
  `state`. Detector signature unchanged.
- **Doggylump (failure modes) / pre-mortem:** Scenario 1 (silent verdict drift)
  is mitigated by the unmodified disk-evidence, corpus-agreement, done-predicate,
  snapshot, and e2e suites plus the independent oracle. Scenario 2
  (fault-ordering regression) is pinned by the A1 test. Scenario 3 (accidental
  coupling of the existence-only clause to content, pre-empting 3.1.2) is pinned
  by `test_done_predicate.py:146-147` asserting stale→`True`.
- **Dinolump (viability):** the seam is exactly what 3.1.2 inherits, matching
  the established deliberate-twin discipline.

## Advisory (non-blocking, carried to implementation)

- A3 — WI4 should also refresh the *signature* spelling in the existing
  dev-guide paragraph at `developers-guide.md:573`, which today reads
  `compile_consistent_exists(working_dir)`. After WI3 changes the signature to
  `(state, working_dir)` (keeping the name, the D-SCOPE default), that line
  becomes stale. WI4 already rewrites this paragraph's surrounding prose, so
  correcting the signature spelling there costs nothing and avoids shipping a
  doc that contradicts the code. Non-blocking because it is a one-token
  correction inside a paragraph WI4 already edits, and the markdown gates do not
  enforce signature accuracy; flagged so the implementer does not leave it
  stale.
- A4 — When WI3 keeps the name `compile_consistent_exists` but the function now
  reads the comparison rather than testing existence, the name is mildly
  misleading. The plan's default (keep the name to minimize the diff and keep
  the residual-window docstring honest) is defensible and explicitly recorded as
  a Decision-Log choice; calling it out so the 3.1.2 implementer, who will flip
  the projection, is not surprised by an `_exists`-suffixed function that no
  longer means existence. Non-blocking.

## Trail followed

`docs/execplans/roadmap-3-1-3.md`, `docs/execplans/roadmap-3-1-3.review-r1.md`,
`docs/issues/audit-3.1.1.md` (Finding 2), `docs/roadmap.md` (tasks 3.1.2/3.1.3),
`docs/novel-ralph-harness-design.md` §§4.2/4.3/5.4 (via the dev-guide and plan
anchors), `docs/developers-guide.md` (compile-model `:316-326`, done-predicate
`:540-586`), `docs/adr-001-deterministic-judgemental-boundary.md`, `AGENTS.md`
(400-line cap, CQS, en-GB Oxford spelling), and the `logisphere-design-review`
skill. Source verified directly: `novel_ralph_skill/state/compile_model.py`,
`disk_evidence.py`, `done_predicate.py`, `state/__init__.py`,
`tests/test_done_predicate.py`, `tests/test_disk_evidence.py`,
`tests/working_corpus/_oracle_disk.py`, plus a repo-wide grep for the clause and
the two new symbols. cuprum's read-only sibling checkout was not consulted
because the diff has no cuprum surface (D-NO-CUPRUM, verified).
