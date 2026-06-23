# Logisphere design review — roadmap 2.2.2 (round 1)

Adversarial pre-implementation review of `docs/execplans/roadmap-2-2-2.md`
(`init`, `set-cursor`, `advance-phase`). Verdict: **Revise**. The plan is
well-grounded — every locked-library and cuprum claim checks out against real
source — but it carries blocking gaps that would derail a novice implementer.

## Sources consulted

- Plan read from disk in full.
- Design: `docs/novel-ralph-harness-design.md` §3.2 (lines 190-205), §3.3-§3.4,
  §4.1 (lines 246-267), §5.1 (lines 372-428), §5.2 (lines 430-456).
- ADRs referenced transitively via design and developers-guide.
- `skill/novel-ralph/references/state-layout.md` schema (lines 58-138) and
  "Initialisation" (lines 230-241).
- Source verified: `novel_ralph_skill/commands/novel_state.py`,
  `state/document.py`, `state/parse.py`, `state/schema.py`, `state/validate.py`,
  `state/__init__.py`; `tests/working_corpus/_builder.py`, `_library.py`;
  `tests/corpus_fixtures.py`; `tests/test_novel_state_check.py`;
  `tests/test_cyclopts_contract.py`; `docs/developers-guide.md` §"State…",
  §"direct-edit guard".
- cuprum read-only sibling: `/data/leynos/Projects/cuprum/cuprum/catalogue.py`
  (`ProjectSettings`/`ProgramEntry`/`ProgramCatalogue` confirmed).
- uv.lock pins: cyclopts 4.18.0, tomlkit 0.15.0, cuprum 0.1.0, pytest-bdd
  >=8.1.0 — all confirmed.
- Cyclopts default command naming verified against the official docs
  (cyclopts.readthedocs.io "Commands": "a command is registered to the function
  name with underscores replaced with hyphens"). So `set_cursor` → `set-cursor`
  and `advance_phase` → `advance-phase` are automatic; the plan's hedge is the
  right posture, NOT a memory-based defect.

## Blocking defects (back to the planner)

### B1 — `build_initial_document` spec is incomplete; following it literally makes `parse_state`/`check` raise `KeyError`

`parse_state` (state/parse.py) is a *strict* boundary: it reads required keys
by subscription with no defaults. The initial document MUST carry every key the
corpus `_build_state_document` emits, or the immediate `check` and the
work-item-2 unit test (`parse_state` over the freshly written doc) raise
`KeyError`/`TypeError` and route to exit 3, never the asserted exit 0. The
plan's prose (`[drafting]` with "critic/fangirl sub-tables") is too loose. The
builder must emit, verbatim per state/parse.py and `_builder.py`:

- `[drafting.critic]`: `pass` (the on-disk key is the keyword `pass`, read at
  parse.py line 123 as `raw["pass"]`), `consecutive_clean`,
  `convergence_target`, and `last_finding_counts` as an inline table with all
  four of `blocker/major/minor/taste`.
- `[drafting.fangirl].last_chapter_passed`.
- `[gates.knitting]` with all of `done_30/done_50/done_80`;
  `[gates.final] .final_pass_complete`.
- `[word_counts]` with `target`, `current = 0`, and `by_chapter` present (an
  empty inline table — parse.py `_word_counts` subscripts `raw["by_chapter"]`).
- `[novel].created_at` (parse.py `_novel` requires it).

The plan names `convergence_target = 1` and the gates, but does not pin `pass`,
`last_finding_counts`, `fangirl.last_chapter_passed`, `word_counts.current`, or
the *required-and-present* empty `by_chapter`. A novice will under-build the
document and fail the very test work item 2 promises to turn green. Fix:
enumerate the full table set in the work-item-2 step (or have it explicitly
derive the shape from `state/parse.py` field-by-field), and add an assertion
that `parse_state(build_initial_document(...))` succeeds *before*
`validate_state`.

### B2 — `set-cursor`/`advance-phase` load path is mis-specified: `_load_or_state_error` cannot be reused as written

The plan's Context section and work item 3 lean on the existing
`_load_or_state_error`, but that helper calls `load_state` → `tomllib`, which
returns a plain mapping, NOT a `tomlkit` `TOMLDocument`. The mutators must
mutate the *live document* (the whole point of ADR-002 and Decision Log D2), so
they must load via `load_document` (tomlkit), not `_load_or_state_error`. The
plan half- acknowledges this ("a reused `_load_or_state_error`-*style* guard"),
but never states that a *new* document-load-and-translate helper is required,
nor that `load_document` raises a *different* fault set than
`STATE_INPUT_ERRORS` was sized for. `tomlkit.parse` raises
`tomlkit.exceptions.ParseError` (a `ValueError` subclass) and `path.read_text`
raises `OSError`; `document_to_state` → `parse_state` then raises `KeyError`/
`ValueError`/`TypeError`. The plan must specify the exact translate boundary
for the document path — either extend `STATE_INPUT_ERRORS`/add a
`_load_document_or_state_error` sibling — and pin it, because
"missing/unparseable state exits 3" is a stated acceptance criterion and the
current `STATE_INPUT_ERRORS` tuple lists `tomllib.TOMLDecodeError`, which the
tomlkit path never raises. This is a real exit-code-contract gap, not a nicety.

### B3 — `advance-phase` "completed-prefix surfaces the skip" is over-claimed; the out-of-order success/refusal mechanism needs proof, and a coherent prior state cannot become out-of-order by advancing

Work item 4 asserts that appending the current phase to `completed` and
advancing `current` makes a *skip or out-of-order* prior state fail
`_check_completed_prefix`. But scrutinise the mechanism against validate.py:

- If the *prior* state is already coherent (the normal harness case),
  `completed`
  is exactly the in-order prefix of `current`. Appending `current` and moving
  to the successor yields a state whose `completed` is the in-order prefix of
  the successor — i.e. still coherent. So a coherent tree NEVER refuses here;
  the only refusals are the terminal-phase and empty-manifest command-level
  preconditions.
- The completed-prefix refusal therefore only fires when the prior state is
  *already incoherent* (its `completed` is not the prefix). That means the
  "out-of-order advance is refused" behavioural scenario (the roadmap success
  criterion) can only be built on an **already-incoherent** starting tree —
  which is a strange thing to call "refuses an out-of-order advance", since the
  input was already broken before the advance.

This is a genuine design-conformance question: design §4.1/§5.1 say
`advance-phase` "refuses any transition that skips a member or completes phases
out of order". `advance-phase` takes **no argument** (the plan's own signature
`advance_phase()`), so it can only ever move to the immediate successor — it is
*structurally incapable* of skipping. The only way it "completes phases out of
order" is if the prior `completed` was already wrong. The plan must either (a)
state explicitly that the refusal guards against advancing *from* an
already-incoherent prior state (and build the BDD scenario on an
`INCOHERENT_VARIANTS` completed-prefix tree, naming which variant), or (b)
reconcile with the design wording, which a reader could read as requiring
`advance-phase` to detect a *target* skip. As written, work item 4's "a tree
whose advance-phase would land on an out-of-order or skipped phase" is
hand-wavy and does not name a concrete, buildable corpus tree. Pin the exact
starting tree and the exact invariant the proposed state violates.

### B4 — Success path for `advance-phase` into `drafting` (populated manifest) is unbuildable from the named corpus fixtures, and the cited example may already be terminal-adjacent

Work item 4 says "advance-phase into drafting … with a populated manifest exits
0" and "from a phase with its predecessor prefix coherent (e.g.
`phase_state_tree` for a non-terminal phase)". But:

- `PHASE_STATES["chapter-planning"]` is a `_pre_drafting_spec` with **empty**
  chapters (`_library.py` lines 67-76, 100-104). So
  `phase_state_tree( "chapter-planning")` advances into `drafting` and hits the
  **empty-manifest refusal** — it cannot be the populated-manifest success case.
- There is no corpus fixture for "chapter-planning with a populated manifest".
  The plan must construct one (via `make_working_tree_spec`/`build_tree` with
  `phase_current="chapter-planning"`, `phase_completed=PHASE_ORDER[:7]`, and a
  non-empty `chapters=`), and must ensure the resulting *advanced* state is
  coherent (cursor at chapter 0 with a populated manifest is coherent; confirm
  no gate/by-chapter-sum invariant trips). The plan gestures at "build it from
  the corpus" but never names the buildable success tree. Specify it.

## Advisory (non-blocking but should be addressed)

- A1 — **`init` overwrite reading is defensible but the design is genuinely
  silent.** Decision Log D1 (refuse, exit 3) is the safer reading and is
  correctly flagged as the Tolerance escalation point. No change required, but
  flag to the reviewer that state-layout.md "Initialisation" frames init as the
  first turn ("working/ does not exist"), so the *existing-state* case is
  undocumented — the refuse reading is a design *decision*, not a derivation.
  Keep it, but surface it to the human reviewer rather than burying it as
  settled.

- A2 — **`init` argument source for `created_at` is generated, not supplied.**
  The plan generates `created_at` via `datetime.now(datetime.UTC)`. Confirm the
  snapshot normalisation (work item 5) and the unit test both exclude it; the
  plan says so, but the work-item-2 unit test enumerates fields to assert and
  should *explicitly exclude* `created_at` to avoid a flaky equality.

- A3 — **`set-cursor` Hypothesis property is marked "optional".** Per AGENTS.md
  line 162 ("Use property tests … when a change introduces an invariant over a
  range of inputs"), the cursor-coherence equivalence (`set-cursor` accepts
  exactly the cursors `validate_state` accepts) IS such an invariant. Treat the
  property as expected, not optional, and run `python-verification` to confirm
  Hypothesis is the adversary (the plan already says to). Downgrade only with a
  recorded reason.

- A4 — **Scope tolerance vs. file count.** Tolerance caps at 9 files; the
  enumerated set is ~8 (command module, `state/initial.py`,
  `state/__init__.py`, mutator test, feature, step, bdd binder,
  developers-guide). If B2's new document-load helper and B4's new success-tree
  fixture push past the cap, the module-size risk (`_state_mutators.py`
  extraction) compounds it. Re-confirm the file budget once B1-B4 are resolved.

- A5 — **`advance-phase` mutating `completed` then validating is
  order-sensitive.**
  The plan appends to `document["phase"]["completed"]` then sets
  `document["phase"]["current"]`. tomlkit array append on a freshly-`init`-ed
  empty `completed = []` array is the same surgical case 2.2.1 verified, but
  the plan should add a comment-preservation/round-trip assertion specifically
  for the *append-to-empty-array* sub-case, which differs from the value-edit
  case 2.2.1 probed. Low risk, but pin it rather than assume the 2.2.1 probe
  covers it.

## Pre-mortem (Doggylump)

Six months on, the harness loop stalls. Working backwards: the most likely
trigger is **B1/B2** — `init` produced a document missing `last_finding_counts`
or `by_chapter`, so the immediately-following `check` raised `KeyError` → exit
3, which the loop (per §3.2) reads as "stop and fix state", not "loop on". The
loop wedges on turn 1 with a freshly-bootstrapped project. Blast radius: every
new novel. Signal missed: the work-item-2 unit test would have caught it IF it
asserted `parse_state(...)` succeeds — but the plan's unit test asserts *field
values*, which presupposes the parse already worked. Prevention designable now:
make "parse_state over the init document succeeds" the first assertion, and
enumerate the full table set (B1).

Second scenario: **B2** — a hand-corrupted `state.toml` (an operator
fat-fingered it before `set-cursor`) raises `tomlkit.exceptions.ParseError`,
which is NOT in `STATE_INPUT_ERRORS`, so it escapes as an uncaught exception →
the shared `run` maps it to… an unhandled crash, not the contracted exit 3. The
"missing/ unparseable exits 3" acceptance criterion silently regresses.
Prevention: pin the tomlkit fault set (B2).

## Alternatives checkpoint (Wafflecat)

The strongest alternative to the document-mutate-then-validate flow is a
**typed-edit-then-reserialise** flow: parse to `State`, build a new `State`
with the cursor/phase changed, re-emit. This is rejected — correctly — by
ADR-002 and Decision Log D2 because it discards comments/layout. The plan picks
the right structural approach; no viable alternative exists that preserves the
lossless round-trip. That is a strong signal the *core* mechanism is sound; the
defects are in specification completeness (B1, B2, B4) and one over-claim (B3),
not in the architecture.

## Verdict

🔄 **Revise.** Architecture is conformant and the library/cuprum claims hold.
Resolve B1-B4 (and ideally A2-A3) before implementation: as written, a faithful
implementer hits a `KeyError` on the first `check` after `init`, an uncaught
parse fault on the corrupt-state path, an un-named BDD starting tree, and an
unbuildable drafting success case. None require relaxing the design; all
require the plan to pin what it currently gestures at.
