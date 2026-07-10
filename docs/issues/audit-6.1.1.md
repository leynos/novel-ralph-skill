# Post-merge audit — roadmap task 6.1.1

Audit of the codebase after roadmap task 6.1.1 ("wordcount reporting and
gate-trigger derivation") merged to `main` at commit `e0c6cf5`. The slice
promotes `wordcount` off the stub onto the shared real-command contract: it
reads the chapter drafts and the typed `state.toml`, derives a per-chapter and
cumulative word-count report — words, percentage of target, the delta against
the chapter target, the 30/50/80% gate triggers, and the distance to the next
knitting gate — and reports the finding read-only (ADR-001). The work is split
across the command body
[`commands/_wordcount.py`](../../novel_ralph_skill/commands/_wordcount.py)
(disk sourcing plus app wiring) and the pure derivation
[`commands/_wordcount_report.py`](../../novel_ralph_skill/commands/_wordcount_report.py)
(`build_report`, `_gate_geometry`, `report_outcome`), with `stub.py` updated to
record that all five console-scripts now drive real apps.

The slice is sound and unusually well covered. The pure report dataclasses and
the gate geometry are pinned by example and boundary unit tests
([`test_wordcount_report.py`](../../tests/test_wordcount_report.py)) and
envelope snapshots
([`test_wordcount_snapshots.py`](../../tests/test_wordcount_snapshots.py));
the wired exit-code contract — exit `0` on a report; exit `3` for an absent
`working/`, an unparseable `state.toml`, and an undecodable `draft.md`; exit `2`
for an unknown `--option`; never exit `4` — is fully pinned in
[`test_wordcount_command.py`](../../tests/test_wordcount_command.py); and the
installed binary is proven end-to-end
([`test_wordcount_e2e.py`](../../tests/test_wordcount_e2e.py)). The users' guide
was updated thoroughly, and the docstrings are detailed.

None of the findings below is a blocking defect; all are low-severity hygiene
items. The dominant themes are (1) a small triplication of the
`STATE_INPUT_ERRORS` → `StateInputError` draft-read wrapper now that `wordcount`
adds a third copy; (2) the `ratio >= threshold` gate-trigger derivation now
re-spelled in a third site with no shared pure helper; (3) two unsynchronized
encodings of the same three gates (`GATE_THRESHOLDS` ratios versus
`KNITTING_PERCENTAGES` integers); (4) a stale developers'-guide paragraph that
still calls `wordcount` (and two others) a stub; and (5) two untested
human-prose branches of `_cumulative_message`.

Trail followed: explored with `leta` (`leta files`, `leta grep`, `leta show`,
`leta refs`) over `commands/_wordcount.py`, `commands/_wordcount_report.py`,
`commands/_recount.py`, `commands/_desloppify.py`, `commands/stub.py`,
`state/wordcount.py`, `state/validate.py`, and `state/done_predicate.py`; traced
history with `git show e0c6cf5 --stat` and `sem`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §3.1/§3.2/§4.5/§5.2/§5.4,
`docs/users-guide.md`, `docs/developers-guide.md` ("Checker/mutator
segregation"), the ExecPlan `docs/execplans/roadmap-6-1-1.md`, prior
`docs/issues/audit-2.3.1.md`, and `AGENTS.md`. Loaded the `leta`, `sem`, and
`python-router` skills. Each finding records a category, location, description,
concrete proposed fix, and severity.

## Finding 1 — `STATE_INPUT_ERRORS` → `StateInputError` draft-read wrapper triplicated

- Category: duplication
- Severity: low
- Location:
  [`commands/_wordcount.py`](../../novel_ralph_skill/commands/_wordcount.py)
  lines 62–101 (`_recount_or_state_error`);
  [`commands/_recount.py`](../../novel_ralph_skill/commands/_recount.py) lines
  43–80 (`_recount_or_state_error`);
  [`commands/_desloppify.py`](../../novel_ralph_skill/commands/_desloppify.py)
  lines 162–207 (`source_chapters`, the `try/except STATE_INPUT_ERRORS` tail).

Three command modules now share the same idiom: call a disk reader
(`recount_words` or `_chapter_text`), catch `STATE_INPUT_ERRORS`, and re-raise as
`StateInputError` so an undecodable draft reaches exit `3` rather than escaping
to the benign exit `1`. `_wordcount` and `_desloppify` even use the identical
message string `f"cannot read chapter drafts: {exc}"`; `_recount` differs only by
`"recount"` in the verb. Each docstring explicitly notes it "mirrors" the others,
which is an acknowledgement of the drift this finding flags. `wordcount` added
the third copy.

Proposed fix: promote a single `read_drafts_or_state_error(working_dir,
manifest)` helper (or a thin `state_error_on(STATE_INPUT_ERRORS, "...")` context
manager) into a shared module — `commands/novel_state.py` already exports
`STATE_INPUT_ERRORS` and `_load_or_state_error`, so it is the natural home — and
have all three call sites delegate to it. This keeps the one fault-routing rule
(which read faults are exit `3`) in a single place, consistent with `wordcount.py`
having already centralized the one counting rule.

## Finding 2 — Gate-trigger derivation `ratio >= threshold` re-spelled in a third site

- Category: duplication
- Severity: low
- Location:
  [`commands/_wordcount_report.py`](../../novel_ralph_skill/commands/_wordcount_report.py)
  line 186 (`_gate_geometry`, `tuple(ratio >= threshold for threshold in
  GATE_THRESHOLDS)`);
  [`state/validate.py`](../../novel_ralph_skill/state/validate.py) lines 267–270
  (`_check_gate_ratio_consistent`, `flag == (ratio >= threshold)` over
  `GATE_THRESHOLDS`);
  [`tests/working_corpus/_oracle.py`](../../tests/working_corpus/_oracle.py)
  `_check_gate_ratio_consistent` (the corpus oracle's copy).

The slice correctly reuses the `GATE_THRESHOLDS` *constant* as a single source of
truth (the docstring is emphatic about not re-spelling the literal). But the
*derivation* — "which gates has this drafted ratio triggered?", i.e.
`tuple(ratio >= t for t in GATE_THRESHOLDS)` after the `target <= 0`
short-circuit — is now written out three times: in the new `_gate_geometry`, in
the validator's invariant 7, and in the test oracle. The validator and the report
must agree on this (the report's whole point is to surface the same triggers the
done-condition checks consume), yet nothing ties them to one expression; a future
change to the tie-break (`>=` versus `>`) would need editing in three places.

Proposed fix: promote a small pure helper `gate_triggers(ratio: float | None) ->
tuple[bool, bool, bool]` (returning all-`False` for a `None`/degenerate ratio)
into the `state` package beside `GATE_THRESHOLDS`, re-export it from
`state/__init__.py`, and have `_gate_geometry` and `_check_gate_ratio_consistent`
both call it. The oracle can stay an independent re-derivation (its job is to be
a second opinion), but production should compute the triggers once.

## Finding 3 — Two unsynchronized encodings of the same three knitting gates

- Category: inconsistency
- Severity: low
- Location:
  [`state/validate.py`](../../novel_ralph_skill/state/validate.py) line 76
  (`GATE_THRESHOLDS: tuple[float, float, float] = (0.30, 0.50, 0.80)`);
  [`state/done_predicate.py`](../../novel_ralph_skill/state/done_predicate.py)
  line 63 (`KNITTING_PERCENTAGES: typ.Final[tuple[int, int, int]] = (30, 50,
  80)`);
  [`commands/_wordcount_report.py`](../../novel_ralph_skill/commands/_wordcount_report.py)
  line 289 (`_cumulative_message`, `(next_gate_threshold or 0.0) * 100`).

The codebase carries the same three gates in two forms: `GATE_THRESHOLDS` as
ratios and `KNITTING_PERCENTAGES` as integer percentages. Each is independently
documented as "the single source of truth" for the gates in its own module, but
nothing asserts `GATE_THRESHOLDS[i] == KNITTING_PERCENTAGES[i] / 100`. `wordcount`
makes the straddle visible: it imports `GATE_THRESHOLDS` (ratios) for the geometry
then converts back to the percentage form inline (`* 100`) in `_cumulative_message`
to render the human "next knitting gate at 50%" line. A future edit that, say,
inserts a 65% gate into one tuple but not the other would silently desynchronize
the validator/report geometry from the review-file naming.

Proposed fix: derive one tuple from the other (e.g. define `GATE_THRESHOLDS =
tuple(p / 100 for p in KNITTING_PERCENTAGES)` or vice versa, in whichever module
should own the canonical form), or add a single assertion/test pinning
`GATE_THRESHOLDS == tuple(p / 100 for p in KNITTING_PERCENTAGES)` so the two
encodings cannot drift. The percentage rendering in `_cumulative_message` should
then read from the canonical percentage source rather than re-deriving `* 100`.

## Finding 4 — Developers' guide still calls `wordcount` (and two others) a stub

- Category: docs-gap
- Severity: low
- Location:
  [`docs/developers-guide.md`](../../docs/developers-guide.md) lines 180–200.

The paragraph reads "`novel-state` (task 2.1.2) and `desloppify` (task 5.1.2)
now drive their real apps; the remaining three are still **stubs**", and
describes the `make_stub_app` "not yet implemented" exit-`2` behaviour as the live
contract for those three. After task 6.1.1, `stub.py`'s own module docstring
(lines 1–13) correctly records that **all five** console-scripts drive real apps
(`novel-state`, `desloppify`, `novel-compile`, `novel-done`, and now
`wordcount`), and line 204 of the same guide already lists `wordcount` among the
read-only checkers. The 180–200 paragraph is therefore stale on two counts: it
under-counts the real apps and overstates how many stubs remain (none do). The
6.1.1 delivery updated the users' guide thoroughly but left this developers'-guide
paragraph behind.

Proposed fix: rewrite the paragraph to state that all five console-scripts now
drive their real Cyclopts apps through the shared `run` wrapper (mirroring
`stub.py`'s docstring), and reframe `make_stub_app` as a retained factory kept
only for the unit tests that pin the stub-result exit-code contract, rather than
as the live behaviour of any entry point.

## Finding 5 — Two `_cumulative_message` human-prose branches are untested

- Category: test-gap
- Severity: low
- Location:
  [`commands/_wordcount_report.py`](../../novel_ralph_skill/commands/_wordcount_report.py)
  lines 279–294 (`_cumulative_message`); tests in
  [`test_wordcount_snapshots.py`](../../tests/test_wordcount_snapshots.py) and
  [`test_wordcount_report.py`](../../tests/test_wordcount_report.py).

`_cumulative_message` has three branches: "no target set"
(`percent_of_target is None`), "all knitting gates reached"
(`next_gate_distance is None`), and the mid-gate "next knitting gate at N%" line.
Only the mid-gate branch is pinned, by the representative-tree snapshot
(`messages: ['drafted 7000 of 20000 words (35.0% of target); next knitting gate
at 50% (3000 words to go)']`). The `target == 0` and past-final-gate tests
(`test_target_zero_envelope`, `test_past_final_gate_envelope`) assert only on the
machine `result` payload, never on `messages`, so the "no target set" and "all
knitting gates reached" prose strings are never exercised. The harness never
parses these lines (ADR-003), so the risk is purely cosmetic regression, but the
branches are genuinely uncovered.

Proposed fix: extend the `target == 0` and past-final-gate snapshot/unit tests to
assert the `messages[0]` string (or add two small direct `report_outcome`/
`_cumulative_message` assertions), pinning the "no target set" and "all knitting
gates reached" wording so a future edit to those lines is caught.

## Finding 6 — `source_state_and_drafts` is public but used only internally, returning a bare 3-tuple

- Category: ergonomics
- Severity: low
- Location:
  [`commands/_wordcount.py`](../../novel_ralph_skill/commands/_wordcount.py)
  lines 104–133 (`source_state_and_drafts`), sole caller at line 159 (`_wordcount`).

`source_state_and_drafts` carries no leading underscore, signalling a public
helper, yet `leta refs` finds its only call site is `_wordcount` in the same
module (plus tests). It returns a positional 3-tuple `(target, manifest,
by_chapter)` that the caller immediately unpacks; the sibling `_recount`/
`_desloppify` sourcing helpers are private (`_recount_or_state_error`,
`source_chapters` — the latter public by the same convention). The bare 3-tuple
is the mild ergonomic smell: an added field would silently shift every unpack.

Proposed fix: either rename to `_source_state_and_drafts` to match the private
convention of its siblings if no external consumer is intended, or, if it is meant
as a reusable sourcing seam (e.g. for a later `--chapter` variant), return a small
frozen dataclass (`target`, `manifest`, `by_chapter`) so the contract is named and
extensible. The rename is the cheaper of the two and is the right default
unless a second consumer is genuinely anticipated.

## Finding 7 — Load-bearing `validate.py:NNN` line citations in docstrings are drift-prone

- Category: docs-gap
- Severity: low
- Location:
  [`commands/_wordcount_report.py`](../../novel_ralph_skill/commands/_wordcount_report.py)
  module docstring lines 16–17 and 33 (`validate.py:263`, `validate.py:261`),
  and `_percent` line 133 (`validate.py:261`).

The new module's docstrings cite specific line numbers in `validate.py`
(`:261` for the `target <= 0` guard, `:263` for the `sum(by_chapter.values())`
numerator) to justify that the report shares the validator's totality guard and
numerator. The citations are accurate today, but line-number references break
silently the moment `validate.py` shifts by an edit elsewhere — exactly the kind
of stale reference prior audits (e.g. audit-2.3.1 Findings 2–3) have repeatedly
caught after unrelated changes. This is a pre-existing house style rather than a
6.1.1 regression, so it is noted lightly.

Proposed fix: replace the `file:line` citations with symbol references
(`validate._check_gate_ratio_consistent`'s `target <= 0` guard and its
`drafted_total` numerator), which `leta` can resolve and which do not drift with
line edits. Apply opportunistically when these docstrings are next touched rather
than as a standalone change.
