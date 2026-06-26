# Post-merge audit — roadmap task 2.3.7

Audit of the codebase after task 2.3.7 ("Make `recount`'s gate-ratio refusal
actionable") merged to `main` at commit `fa6c1af`. The task enriched the
pure-state `gate-ratio-consistent` violation detail so each knitting-gate breach
names the gate, its threshold, the drafted ratio, and the breach direction; it
added a command-layer remedy (`_gate_ratio_remedy`) wired through a new optional
`remedy` keyword on `_refuse_if_incoherent`, so a refused `recount` carries
direction-correct operator advice (upward: integrate the pass then
`set-gate --knitting-NN`; downward: adjudicate, never prescribe the repair
verb); and it documented the recount-gate coupling across the developers' guide,
the users' guide, and the state-layout reference.

Trail followed: `docs/novel-ralph-harness-design.md` §§3.3/4.1/5.2/5.4,
`docs/developers-guide.md` §"The recount-gate coupling", `docs/users-guide.md`,
`docs/roadmap.md` task 2.3.7, `docs/execplans/roadmap-2-3-7.md` and its two
Logisphere review rounds (design-review B2), `skill/novel-ralph/references/state-layout.md`,
`docs/adr-001` (deterministic/judgemental boundary), `docs/adr-010` (gate/drafting
mutators), `AGENTS.md` (quality gates, the 400-line cap, CQS), and the
`python-router` skill (Python work, routing to data-shapes for the gate
descriptor proposal). Navigation and history were traced with `leta` and `sem`;
fallback `grep` was used to enumerate every knitting-gate constant site. Files
inspected: `novel_ralph_skill/commands/_recount.py`,
`novel_ralph_skill/commands/_state_mutators.py`,
`novel_ralph_skill/state/validate.py`,
`novel_ralph_skill/commands/_gate_drafting_mutators.py`,
`novel_ralph_skill/state/done_predicate.py`,
`novel_ralph_skill/commands/_wordcount_report.py`,
`tests/test_recount_actionable_unit.py`, `tests/test_recount_e2e.py`,
`tests/features/recount.feature`, `tests/steps/recount_steps.py`,
`tests/test_validate_state_details.py`.

The merged change is high quality and tightly scoped. The checker/mutator split
is respected (the validator emits a CLI-agnostic *description*; the command layer
owns the *remedy*), the dual-direction behaviour is proven at unit, BDD, and
installed-binary e2e levels, the `remedy` keyword defaults to `None` so every
existing caller is untouched, and the docs describe the coupling consistently in
three places. The findings below are refinements; none is a defect in the merged
behaviour.

## Finding 1 — `_gate_ratio_remedy` re-derives the validator's entire gate-ratio computation (severity: medium)

**Category:** duplication

**Location:** `novel_ralph_skill/commands/_recount.py` `_gate_ratio_remedy`
lines 150-181, against `novel_ralph_skill/state/validate.py`
`_check_gate_ratio_consistent` lines 275-311.

**Description:** The remedy builder and the validator predicate independently
recompute the same five facts in the same shape: the `target <= 0` short-circuit
guard (`_recount.py` line 151 vs `validate.py` lines 292-293), the
`drafted_total = sum(state.word_counts.by_chapter.values())` numerator
(`_recount.py` line 153 vs `validate.py` line 294), `ratio = drafted_total /
target` (line 154 vs line 295), the `flags = (knitting.done_30, done_50,
done_80)` tuple (line 156 vs line 297), and the per-gate `flag != (ratio >=
threshold)` disagreement test zipped over `GATE_THRESHOLDS`
(`_recount.py` lines 159-163 vs `validate.py` lines 298-304). The remedy is
called only on the refusal path, on the *same* `state` the validator just
rejected, yet it recomputes which gates disagree from scratch rather than
consuming the validator's verdict. The two notions of "which gate disagrees" are
therefore kept in lock-step only by hand: if the validator's disagreement rule
ever changed (a tolerance, a different numerator), the remedy would silently
advise on a different gate set than the one the refusal named, and no test pins
the two enumerations against each other — the unit tests assert the remedy text
but never assert that the gates the remedy addresses equal the gates the
`gate-ratio-consistent` detail named.

**Proposed fix:** Have the remedy consume the breach the validator already
found rather than recomputing it. Two viable shapes: (a) extract a pure
`gate_ratio_disagreements(state) -> tuple[GateDisagreement, ...]` helper in the
`state` package (each item carrying `name`, `threshold`, `ratio`, and the
`crossed` direction) that *both* `_check_gate_ratio_consistent` and
`_gate_ratio_remedy` consume — the validator turns each into a `Violation`
detail, the remedy turns each into an advice line; or (b) have
`_refuse_if_incoherent` hand the `remedy` callable the `verdict` it already
computed (line 182) so the remedy reads the `gate-ratio-consistent`
`Violation` rather than re-deriving from `state`. Either removes the parallel
computation and makes "the gate the refusal names" and "the gate the remedy
advises" provably the same set. Add a test asserting the remedy line count and
gate identities match the `gate-ratio-consistent` violation's enumerated gates.

## Finding 2 — three parallel encodings of the knitting-gate triple, none shared (severity: medium)

**Category:** duplication

**Location:** `novel_ralph_skill/state/validate.py` `_KNITTING_GATE_NAMES`
line 252 and `GATE_THRESHOLDS` line 76; `novel_ralph_skill/commands/_recount.py`
`_KNITTING_GATE_REPAIRS` lines 50-54; `novel_ralph_skill/commands/_gate_drafting_mutators.py`
`_KNITTING_KEYS` lines 70-74; with `novel_ralph_skill/state/done_predicate.py`
`KNITTING_PERCENTAGES` line 63 a fourth integer-percentage encoding of the same
three gates.

**Description:** The three knitting gates (`done_30`/`done_50`/`done_80`, their
0.30/0.50/0.80 thresholds, their 30/50/80 integer percentages, and their
`--knitting-NN` CLI flags) are now encoded as four separate parallel tuples
across four modules, each ordered "by hand" to line up with `GATE_THRESHOLDS`
via `zip(..., strict=True)`. `validate.py` pairs names with thresholds;
`_recount.py` pairs names with CLI flags and *re-derives* the integer percentage
with `int(threshold * 100)` (line 165); `_gate_drafting_mutators.py` pairs CLI
arg names with disk keys; `done_predicate.py` already owns the integer
percentages as `KNITTING_PERCENTAGES = (30, 50, 80)` — the very value
`_recount.py` recomputes. The orderings agree only because each author kept them
agreeing; nothing structurally binds them. Adding or reordering a gate would
require four coordinated edits with no compiler or test catching a missed one
(the `strict=True` zips catch length mismatches but not a transposed pair).

**Proposed fix:** Introduce one canonical gate descriptor — e.g. a frozen
`KnittingGate` `msgspec.Struct`/`dataclass` sequence in the `state` package
(`flag_name`, `threshold`, `percent`, `cli_flag`, `disk_key`) — and derive the
existing tuples from it (`GATE_THRESHOLDS`, `_KNITTING_GATE_NAMES`,
`_KNITTING_GATE_REPAIRS`, `_KNITTING_KEYS`, and `KNITTING_PERCENTAGES` all become
projections of one source). This makes gate identity a single edit site and lets
the `python-data-shapes` skill's tagged-record guidance enforce the field
relationships. Pin the projection equalities with a test so a future divergence
fails loudly. (Scope note: this touches four modules and is a candidate roadmap
item rather than a drive-by; recorded as such below.)

## Finding 3 — the `.0f` percentage in the remedy can contradict the threshold it describes (severity: low)

**Category:** inconsistency

**Location:** `novel_ralph_skill/commands/_recount.py` `_gate_ratio_remedy`
line 157 (`percent = f"{ratio * 100:.0f}"`) feeding the downward line at lines
174-180.

**Description:** The remedy renders the recounted ratio as a rounded whole
percent, while the upward/downward decision uses the exact `ratio >= threshold`
comparison. For a ratio in the half-open band just below a threshold — e.g.
`ratio = 0.296` with `done_30 = true` — `crossed = ratio >= 0.30` is `False`, so
the **downward** line fires, but `f"{0.296 * 100:.0f}"` renders `"30"`. The
operator then reads "recount left drafting below the 30% knitting threshold
(drafts now at 30% of target)" — internally contradictory prose that claims the
drafts are simultaneously below 30% and at 30%. The validator's own detail avoids
this because `_gate_ratio_disagreement` renders `ratio:.4f` (`0.2960`), so the
*same refusal envelope* carries both a precise four-decimal ratio (from the
violation detail) and a rounded whole-percent (from the remedy) for one quantity.
No test exercises a near-boundary ratio — every fixture ratio (0.34, 0.55, 0.86)
rounds cleanly away from its threshold, so the contradiction is latent.

**Proposed fix:** Either (a) render the remedy percentage with one decimal place
(`{ratio * 100:.1f}`) so a sub-threshold value reads `29.6%` and cannot collide
with the integer threshold it sits below, or (b) round toward the safe side per
direction (floor for the downward "below" line, so 0.296 → "29%"; ceil is not
needed upward because crossing already implies `ratio >= threshold`). Option (a)
is simpler and also resolves the precision mismatch with the validator detail in
the same envelope. Add a parametrized unit case at a near-boundary ratio
(e.g. `0.296`, downward) asserting the rendered percent does not equal the
threshold integer.

## Finding 4 — the same envelope describes one breach in two vocabularies (severity: low)

**Category:** inconsistency

**Location:** `novel_ralph_skill/state/validate.py` `_gate_ratio_disagreement`
lines 268-272 ("above"/"below", "drafted ratio 0.3400 is above threshold 0.30")
versus `novel_ralph_skill/commands/_recount.py` `_gate_ratio_remedy`
lines 167-180 ("crossed the 30% knitting threshold"/"left drafting below the 30%
knitting threshold").

**Description:** On a refusal both strings land in the exit-3 envelope's
`messages` (the violation detail first, then the remedy line — assembled in
`_refuse_if_incoherent` lines 192-195). They describe the identical fact in
deliberately different registers: the validator says "done_30=False but drafted
ratio 0.3400 is above threshold 0.30"; the remedy says "recount crossed the 30%
knitting threshold (drafts now at 34% of target)". This is defensible — the
detail is the machine-flavoured description and the remedy is the operator
instruction — and the checker/mutator split is the reason they live apart. But an
operator reading the raw envelope sees the same gate described with two different
ratio formats (0.3400 vs 34%) and two different direction words (above vs
crossed), which reads as redundancy rather than escalation. This is a presentation
seam, not a correctness issue; flagged at low severity because it is the kind of
duplicated-but-divergent prose AGENTS.md's "say a thing once" guidance targets.

**Proposed fix:** Decide the envelope's intended reading and align to it. If the
detail and remedy are meant to be complementary (description then instruction),
add a one-line comment at the `details.extend(remedy(state))` site
(`_state_mutators.py` line 194) stating that the remedy line intentionally
re-states the detail in operator-actionable terms, so a future reader does not
"deduplicate" them. If they are meant to be a single message, fold the threshold
percentage and direction word into one shared formatter consumed by both (this
dovetails with Finding 1's shared-disagreement helper). The lowest-cost change is
the comment; the cleaner change is the shared formatter.

## Finding 5 — no test pins the remedy's gate set against the violation's gate set (severity: low)

**Category:** test-gap

**Location:** `tests/test_recount_actionable_unit.py` (the whole module) against
the coupling between `_check_gate_ratio_consistent` and `_gate_ratio_remedy`.

**Description:** The unit suite proves the remedy emits the right *text* per
direction and that the multi-gate case fans out one line per gate, and the
e2e/BDD suites prove the message reaches the user-visible envelope. None of them
asserts the invariant that makes the two-computation design (Finding 1) safe:
that the set of gates the remedy advises on is exactly the set of gates the
`gate-ratio-consistent` `Violation.detail` enumerates. The downward test does
assert "no `set-gate` verb leaks" globally, which is a partial guard, but there
is no positive assertion tying remedy lines to the validator's named gates. If
Finding 1 is left as-is (two independent computations), this is the test that
would catch a future desynchronisation; if Finding 1 is fixed (shared helper),
this test pins the contract the refactor must preserve.

**Proposed fix:** Add a unit test that, for a refusal carrying a
`gate-ratio-consistent` violation, parses the gate names out of the violation
detail and asserts they equal the gate names addressed by the remedy lines
(upward and downward alike), and that the line counts match. This is cheap with
the existing corpus builder and closes the seam regardless of which Finding 1
option is chosen.

## Finding 6 — `_gate_ratio_remedy` lives in the command module but is pure and untested in isolation (severity: low)

**Category:** separation-of-concerns

**Location:** `novel_ralph_skill/commands/_recount.py` `_gate_ratio_remedy`
lines 120-181.

**Description:** `_gate_ratio_remedy` is a pure `State -> list[str]` function with
no I/O, no document handling, and no dependence on anything else in `_recount.py`
beyond the module-private `_KNITTING_GATE_REPAIRS`. It is the natural peer of
`validate.py`'s `_gate_ratio_disagreement` (also pure, also gate-ratio prose) but
sits in the command layer purely so the CLI verb stays out of the validator
(design §3.3) — a sound boundary. However, it is exercised only indirectly through
`recount()` (which requires building a working tree, monkeypatching `chdir`, and
catching `StateInputError`); there is no direct unit test of the pure function
over a constructed `State`. The result is that a pure, table-driven text function
is only ever tested through a disk-and-process harness, which is slower and
couples the remedy's tests to the recount plumbing.

**Proposed fix:** Keep the function in the command layer (the §3.3 boundary is
correct) but add a small direct unit test that constructs a `State` (via the
corpus spec → `document_to_state`, no disk run of `recount`) and asserts
`_gate_ratio_remedy(state)` over the upward, downward, multi-gate, and
no-disagreement (empty-list) cases. This makes the pure function's behaviour
pinnable without the process harness and documents the empty-list no-op path
(mentioned in the docstring lines 130-131) that the current tests never assert.
If Finding 1's shared-helper extraction lands, this test moves to the extracted
helper.
