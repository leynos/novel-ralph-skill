# Post-merge audit — roadmap task 7.2.4

Task 7.2.4 finished the scan-shape relocation 7.2.3 began: it repointed the
runtime straggler (`commands/_desloppify.py`) and the stale Sphinx
cross-references off the `rulepack.detect` re-export and onto the neutral home,
`novel_ralph_skill/loaderkit/scan.py`; pruned the now-orphaned re-export from
`rulepack.detect.__all__`; and added a regression test
(`test_detect_no_longer_reexports_scan_shapes`) pinning that the rule-pack
detector no longer advertises ownership of `ScannedChapter`/`LineHit`. This
closed Findings 1 and 3 of the 7.2.3 audit. The `ledger → rulepack` and
command → `rulepack` domain edges the relocation targeted are now gone, and one
neutral home (`loaderkit.scan`) owns the two scan shapes.

This audit reviews the merged state at `origin/main` (commit `76165ea`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-separation (CQS) issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a location and a concrete proposed fix.

The verdict is that the spine is in strong shape. Docstring coverage is gated at
100% (`[tool.interrogate] fail-under = 100`), the contract runner keeps its pure
projection (`build_envelope`) separate from its side-effecting seam
(`run`/`_emit`), and the file-fault error formatters are already single-sourced
through `state_sourcing._file_fault_error`. The material residue is the
*unfinished simplification half* of the 7.2.x consolidation, which the roadmap
already tracks as tasks 7.8.1, 7.8.2, and 7.4.1: the `line_hit` callback is a
vacuous indirection over `loaderkit.scan`'s own type; the two detectors still
hand-clone a scan-aggregate loop; `scan_pattern` still returns a count that is
always `len(lines)`; and the per-command draft-read-and-wrap envelope is still
copied across six command boundaries. This audit re-verifies each against the
post-7.2.4 code so the roadmap items carry current line evidence, and records one
low-severity test-seam observation that the roadmap does not yet name explicitly.

Documentation and skills relied on for this audit:
`docs/novel-ralph-harness-design.md` (§6, §6.1), `docs/developers-guide.md`
("The shared loader primitives (`loaderkit`)"), `docs/adr-001`, `docs/adr-003`,
`docs/issues/audit-7.2.3.md` (the prior pass this task closes out),
`docs/roadmap.md` (§7.4, §7.8), and `AGENTS.md` (quality gates, 400-line file
cap, en-GB Oxford spelling). Code navigation used `leta`; history was traced with
`sem diff --from HEAD~1 --to HEAD`.

## Finding 1 — The `line_hit` callback is still a vacuous indirection over the module's own type

- **Category:** ergonomics
- **Severity:** medium
- **Location:** `novel_ralph_skill/loaderkit/scan.py:65-104` (`scan_pattern`'s
  `line_hit` parameter and the per-hit `line_hit(...)` call), with the
  byte-identical callback supplied at
  `novel_ralph_skill/rulepack/detect.py:207` and
  `novel_ralph_skill/ledger/detect.py:245`
  (`line_hit=lambda chapter, line: LineHit(chapter=chapter, line=line)`).

`scan_pattern` takes a `line_hit: Callable[[int, int], LineHit]` factory and
constructs every hit through it. The module docstring (`scan.py:13-15`) still
justifies the seam as supplying "a `line_hit` constructor so this module never
imports a pack-domain hit type". That rationale was true under 7.2.2, when
`LineHit` lived in `rulepack.detect`. It is now circular: `LineHit` is defined in
`loaderkit/scan.py` itself (lines 49-62), so the callback constructs the very type
the module owns and already imports for its own annotations. Both call sites
pass the identical forwarding lambda, so the abstraction is pure overhead —
a duplicated closure allocated inside each detector's per-entity loop. 7.2.4 did
not touch this; it remains exactly as the 7.2.3 audit (Finding 2) recorded, and
the roadmap already reroutes it to task 7.8.1.

- **Proposed fix:** Execute roadmap 7.8.1. Drop the `line_hit` parameter and have
  `scan_pattern` construct `LineHit(chapter=…, line=…)` directly; remove the
  duplicated lambda from both `rulepack.detect.detect` and
  `ledger.detect.detect_ledger`; and delete the now-circular "never imports a
  pack-domain hit type" rationale from the `scan.py` docstring and the
  developers' guide. The AST-scoped guard test already proves the module's
  neutrality structurally, so the prose claim is redundant as well as stale.

## Finding 2 — The `line_hit`-callback contract test now pins a seam with no remaining purpose

- **Category:** test-gap
- **Severity:** low
- **Location:**
  `tests/test_loaderkit_scan.py:141-167`
  (`test_scan_pattern_builds_every_hit_via_line_hit_callback`).

This test injects a recording double as `line_hit` and asserts every returned hit
`is` the shared sentinel the double returns, proving `scan_pattern` builds hits
"only through the supplied factory". The test exists to verify the very seam
Finding 1 shows is now vacuous — it pins a factory hook with no production
consumer that varies the factory. Once 7.8.1 removes the `line_hit` parameter,
this assertion becomes untestable (there is no factory to record), so the test
must be retired or rewritten rather than left to rot. Its genuinely useful
assertions — the scan-order `calls == [(3, 1), (3, 2), (3, 2), (7, 1)]` sequence
and the `count == 4` per-line tally — are independent of the callback and worth
preserving.

- **Proposed fix:** As part of 7.8.1, replace this test with a direct-construction
  equivalent that scans the same two-chapter corpus and asserts the resulting
  `LineHit` tuple equals the expected `(chapter, line)` sequence in scan order,
  retaining the per-line-count and scan-order coverage while dropping the
  factory-identity assertion. This keeps the behavioural pin (line numbers are
  exact and one-based, `.` does not cross `\n`) without pinning the removed seam.

## Finding 3 — `detect` and `detect_ledger` still hand-clone a scan-aggregate skeleton

- **Category:** similarity
- **Severity:** low
- **Location:** `novel_ralph_skill/rulepack/detect.py:173-222` (`detect`) and
  `novel_ralph_skill/ledger/detect.py:215-251` (`detect_ledger`).

Both detectors share the same outer loop shape: iterate the entity collection
(`pack.rules` / `ledger.devices`), call
`count, lines = scan_pattern(entity.compiled, chapters, line_hit=…)`, append
`_finding(entity, …)`, then assemble a report with
`passed=all(f.passed for f in findings)`. The bodies diverge only in the entity
attribute, the `total_words` denominator (rule-pack-only), the `_finding`
signature, and the report type. This is the thinned residue the 7.2.x
consolidation left: the inner scan body is shared via `scan_pattern`, but the
aggregation loop is still cloned per detector. Roadmap 7.8.2 already tracks it,
sequenced after 7.8.1 because retiring the callback unblocks a clean extraction.

- **Proposed fix:** Execute roadmap 7.8.2. After 7.8.1 removes the `line_hit`
  lambda, lift the shared scan-and-`_finding` loop into a small `loaderkit`
  helper parameterized on each pack's per-entity `_finding` projection, leaving
  each detector to assemble only its own report (which carries the
  domain-specific `total_words`/report type). If the divergence is judged to
  outweigh the saving, leave the loops and add a one-line comment in each noting
  the deliberate parallel, so the pair is not later re-merged in a way that
  reintroduces the `total_words` coupling.

## Finding 4 — `scan_pattern` returns a count that is always `len(lines)`

- **Category:** cqs
- **Severity:** low
- **Location:** `novel_ralph_skill/loaderkit/scan.py:65-104` (`scan_pattern`
  returns `tuple[int, tuple[LineHit, ...]]` as `return len(hits), tuple(hits)`).

`scan_pattern`'s return pairs a `count` with the `lines` tuple, but `count` is
always exactly `len(lines)`. Both call sites destructure
`count, lines = scan_pattern(...)` and thread both onward, so the redundant
scalar propagates through the detector plumbing even though `count == len(lines)`
is an invariant nothing documents. This is mild redundant API surface — a read
value and a derive value bundled where the derive value cannot disagree with the
tuple. Roadmap 7.8.2 folds the removal into the same pass as the skeleton
extraction.

- **Proposed fix:** As part of 7.8.2, return only `tuple[LineHit, ...]` and let
  the shared aggregate helper take `len(...)` where it needs the count (both
  current callers already hold the tuple). This removes a value that cannot
  disagree with the tuple and trims the `_finding` plumbing accordingly.

## Finding 5 — The draft-read-and-wrap envelope is copied across six command boundaries

- **Category:** duplication
- **Severity:** medium
- **Location:** the
  `except STATE_INPUT_ERRORS as exc: raise _draft_read_error(<dir>) from exc`
  draft-read envelope at `novel_ralph_skill/commands/_recount.py:95-97`,
  `_wordcount.py:100-102`, `_desloppify.py:210-212`, `_novel_done.py:91-92`,
  `novel_state.py:145-147`, and `_compile.py:139-144` /
  `_compile.py:218-223`.

Six command boundaries each read a chapter's `draft.md` (directly or via
`recount_words`) inside a `try` and re-raise any non-`FileNotFoundError` read
fault as the exit-`3` `StateInputError` through the shared `_draft_read_error`
formatter. The *message* is already single-sourced (`_draft_read_error`), but the
read-loop-plus-except envelope around it is hand-copied at each site, and the
"cannot drift apart" guarantee the docstrings assert rests on six matching copies
of the same `except` arm. This is precisely the duplication roadmap 7.4.1 targets:
a shared `read_chapter_draft` helper in the state package would own the
`chapter-NN/draft.md` path, the `FileNotFoundError`-as-undrafted boundary, *and*
the exit-`3` re-raise, making the cross-module "cannot drift" claim structurally
true rather than copy-kept.

- **Proposed fix:** Execute roadmap 7.4.1 (and its companion 7.4.2 for the
  open-coded `chapter-{number:02d}` segment). Introduce one
  `read_chapter_draft` helper that derives the draft path, absorbs
  `FileNotFoundError` as an absent chapter, and re-raises every other read fault
  as `StateInputError` via `_draft_read_error`. Have `_desloppify`, `_wordcount`,
  `_recount`, `_novel_done`, `novel_state`, and `_compile` consume it so the
  read-and-wrap envelope lives in one place, and pin it with a test so it cannot
  re-fork.

## Summary

The 7.2.4 merge is clean and finishes the relocation half of step 7.2: the last
runtime and docstring stragglers now reach the scan shapes through
`loaderkit.scan`, the orphaned `rulepack.detect` re-export is pruned, and a
regression test pins that the rule-pack detector no longer advertises the shapes.
The single-home hypothesis for the scan primitives is settled. No new
un-tracked structural defects surfaced.

The findings recorded here are the *simplification* residue the consolidation
deliberately deferred, and four of the five map directly onto existing roadmap
items: the now-circular `line_hit` callback and its stale rationale (7.8.1,
Finding 1), the contract test that pins that vacuous seam (a low-severity
companion to 7.8.1, Finding 2), the hand-cloned scan-aggregate skeleton and the
redundant `scan_pattern` count return (7.8.2, Findings 3 and 4), and the
draft-read-and-wrap envelope copied across six command boundaries (7.4.1,
Finding 5). The audit adds no new roadmap section; it re-verifies these against
the post-7.2.4 code with current line evidence so the rerouted tasks carry an
accurate inventory, and flags that the `line_hit` contract test must be rewritten
(not merely deleted) when 7.8.1 lands, preserving its scan-order and
per-line-count assertions.
