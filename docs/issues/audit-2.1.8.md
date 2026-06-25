# Post-merge audit — roadmap task 2.1.8

Audit of the codebase after roadmap task 2.1.8 ("Reconcile state-layout.md with
the emitted state schema") merged to `main` at commit `237e839`. The slice
documents the two emitted fields beta testing found missing from the skill
reference — a top-level `chapters = []` array and a
`[drafting.critic].convergence_target` key — by adding them to
[`skill/novel-ralph/references/state-layout.md`](../../skill/novel-ralph/references/state-layout.md),
and adds a guard
([`tests/test_state_layout_schema_guard.py`](../../tests/test_state_layout_schema_guard.py))
that fails if the schema `novel-state init` emits ever again carries a leaf or
table header absent from the reference's `## state.toml schema` fence.

The slice is sound and discharges its Success clause. The guard derives its
required leaf-name and table-header nets from the *serialised* dump of
`build_initial_document(...)` rather than a type walk, so the documented fence
must mirror the textual shape `init` writes; the two known emitted-vs-fence shape
mismatches (the parent-only `[gates]` table emitting no bare header, and the
empty `chapters = []` leaf documented as the populated `[[chapters]]` block) fall
out by construction and are checked separately. The reference now documents
`convergence_target` in both the schema fence and the "Critic sub-state" prose,
and the chapter manifest in the "Chapter manifest" section. The guard, the
reference, and the emitter (`state/initial.py`) agree on the emitted key set.

None of the findings below is a blocking defect. The dominant theme is a
*value-semantics gap the new guard does not close*: the guard pins key and
header *presence* but never a field's *value*, and the freshly-initialised
critic sub-state (`pass`, `consecutive_clean`, `convergence_target`) is not
pinned by any test, so the one place a value can drift — the inline
`pass = 1` documented as "0 means no pass run yet" — is both an undocumented
contradiction and uncaught by a regression. Secondary themes are a *docs-gap*
(the new guard has no developers-guide entry, unlike its sibling write-recipe
guard) and *minor robustness/duplication* points in the guard's helpers.

Trail followed: created a `git-donkey` worktree off `origin/main`; explored
with `leta`/`grep` and direct reads over
[`state/initial.py`](../../novel_ralph_skill/state/initial.py),
[`state/validate.py`](../../novel_ralph_skill/state/validate.py),
[`state/parse.py`](../../novel_ralph_skill/state/parse.py),
[`state/schema.py`](../../novel_ralph_skill/state/schema.py),
[`tests/test_state_layout_schema_guard.py`](../../tests/test_state_layout_schema_guard.py),
[`tests/test_state_layout_reference.py`](../../tests/test_state_layout_reference.py),
[`tests/test_state_initial.py`](../../tests/test_state_initial.py), and
[`tests/working_corpus/_builder.py`](../../tests/working_corpus/_builder.py);
ran `uv run python -m pytest` over the two layout suites (75 passed) and dumped
`build_initial_document(...)` to confirm the emitted shape; traced history with
`git show 237e839`. Source of truth consulted:
[`novel-ralph-harness-design.md`](../../docs/novel-ralph-harness-design.md)
(§5.1 schema, §5.2 invariants),
[`state-layout.md`](../../skill/novel-ralph/references/state-layout.md),
[`developers-guide.md`](../../docs/developers-guide.md) ("Shared test
scaffolding" and "The state-layout direct-edit guard"),
[`roadmap.md`](../../docs/roadmap.md) §2.1.8, and
[`AGENTS.md`](../../AGENTS.md) (the 400-line cap and CQS conventions). Skills
relied on: `python-router` (reviewing the emitter and guard), `leta`
(navigation), and `git show` (history).

Each finding records a category, location, description, proposed fix, and
severity.

## 1. The initial critic `pass = 1` contradicts the reference's "no pass run yet"

- **Category:** inconsistency
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/state/initial.py`](../../novel_ralph_skill/state/initial.py)
  `_drafting_table` (line 93: `critic["pass"] = 1`);
  [`skill/novel-ralph/references/state-layout.md`](../../skill/novel-ralph/references/state-layout.md)
  schema fence (line 91: `pass = 1  # 0 means no pass run yet`) and "Critic
  sub-state" prose (line 171).

A freshly initialised novel has run zero critic passes — `phase.current` is
`premise`, the cursor is zeroed, and `last_finding_counts` is all zeros — yet
`build_initial_document` emits `pass = 1`. The reference's own inline comment
documents the field as "`0` means no pass run yet", so the emitted value
contradicts the documented semantics: by the reference, an init state that has
run no passes should carry `pass = 0`, not `1`. The corpus builder
([`tests/working_corpus/_builder.py`](../../tests/working_corpus/_builder.py)
line 67) emits `pass = 1` too, so the emitter is internally consistent with the
test corpus, but neither the design (§5.1/§5.2) nor the reference explains why
init seeds `pass = 1` rather than the documented "no pass run yet" value of `0`.
This is precisely the class of schema-vs-reference drift task 2.1.8 set out to
close, but it slips through because the 2.1.8 guard checks key *presence*, not
field *values* (see finding 2). It is a documentation/semantics inconsistency,
not a validator breach — `pass` carries no §5.2 invariant — but a reader
reconciling the reference against a real `init` output will find the comment
and the value disagree.

**Proposed fix:** decide the intended initial value and make all three sources
agree. Either (a) seed `pass = 0` in both `state/initial.py` and the corpus
builder so the emitted value matches the "no pass run yet" comment, or (b) keep
`pass = 1` and correct the reference comment and prose to state that init seeds
`pass = 1` (the first pass is numbered 1 and is pending, not run), recording the
rationale next to the emitter. Option (b) is the lower-risk change because it
touches no emitted state or corpus fixture; whichever is chosen, the reference
comment and the emitter must stop disagreeing.

## 2. The schema guard pins key presence but never a field value

- **Category:** test-gap
- **Severity:** low
- **Location:**
  [`tests/test_state_layout_schema_guard.py`](../../tests/test_state_layout_schema_guard.py)
  (the whole module);
  [`tests/test_state_initial.py`](../../tests/test_state_initial.py)
  (`test_initial_document_parses_then_carries_initial_fields`, lines 34-51).

The 2.1.8 guard derives leaf names and table headers from the emitted dump and
asserts each *name* appears as documented TOML syntax in the reference fence. It
deliberately "checks key names and table headers, never values" (module
docstring line 61). Separately, `test_state_initial.py` pins the initial
`phase`, `chapters`, and `word_counts` values but asserts *nothing* about the
critic sub-state: the emitted `pass = 1`, `consecutive_clean = 0`, and
`convergence_target = 1` are not pinned anywhere. The consequence is that the
exact field most likely to drift — the `pass` seed that already contradicts the
reference (finding 1) — could change from `1` to `0` (or vice versa) with the
full suite still green, because no test asserts its value and the guard asserts
only that the *name* `pass` is documented. The new field 2.1.8 reconciled,
`convergence_target`, is likewise unpinned at the initial-document level; a
regression that seeded it as `0` would pass `init`'s own coherence check only
because `validate_state` happens to reject a sub-1 target elsewhere, not because
any initial-document test guards the seeded `1`.

**Proposed fix:** add a focused assertion to
`test_initial_document_parses_then_carries_initial_fields` (or a sibling test)
pinning the initial critic sub-state — `state.drafting.critic.pass_number`,
`consecutive_clean`, and `convergence_target` — to their intended values, with
a comment naming the design clause (§5.1 default convergence ceiling of 1). This
closes the value-drift gap the name-only guard leaves open and gives finding 1's
chosen value a regression anchor. It is a test addition only; no production code
changes.

## 3. The new schema-drift guard has no developers-guide entry

- **Category:** docs-gap
- **Severity:** low
- **Location:**
  [`docs/developers-guide.md`](../../docs/developers-guide.md) ("The
  state-layout direct-edit guard" section, lines 1019-1044);
  [`tests/test_state_layout_schema_guard.py`](../../tests/test_state_layout_schema_guard.py).

The developers' guide carries a dedicated subsection documenting the *sibling*
guard, `test_state_layout_reference.py` (the direct-edit write-recipe scanner),
explaining what it scans, what it leaves untouched, and which roadmap tasks
shaped it. The new 2.1.8 guard, `test_state_layout_schema_guard.py`, is a
distinct and equally load-bearing tripwire — it is the only thing preventing the
reference fence from silently falling out of step with what `init` emits — yet
it gets no equivalent guide entry. A developer who adds a leaf or table to
`build_initial_document` will hit this guard on `make test` with no prior pointer
in the guide to tell them the reference fence must be updated in step. The two
guards are easily confused (both scan `state-layout.md`, both read it through
`read_repo_text`), so the absence of a paired entry is a discoverability gap.

**Proposed fix:** add a short "The state-layout schema-drift guard" subsection
to the developers' guide alongside the existing direct-edit-guard subsection,
stating that the guard derives the required leaf and header nets from the
serialised `build_initial_document(...)` dump, that adding an emitted field
obliges a matching line in the `## state.toml schema` fence, and that the two
documented exclusions (`gates` parent-only header, `chapters` empty-array leaf)
are deliberate. Cross-reference design §5.1 and roadmap 2.1.8.

## 4. The guard reaches into a hardcoded inline-table path with no clear failure

- **Category:** ergonomics
- **Severity:** low
- **Location:**
  [`tests/test_state_layout_schema_guard.py`](../../tests/test_state_layout_schema_guard.py)
  `_emitted_leaf_names` (lines 134-136).

To recover the inner names of the `last_finding_counts` inline table — which
serialise on one physical line and so are not their own `key =` lines — the
helper subscripts `document["drafting"]["critic"]["last_finding_counts"]` with
a hardcoded three-segment path. The subscription is correct for today's schema,
but if a future slice relocates or renames the inline table the helper raises a
bare `KeyError` at module import time (the net is computed at module level, line
275), aborting *collection* of the whole module with an opaque traceback rather
than a guard failure naming the drift. The guard's reason for existing is to
turn schema drift into a legible test failure; this one path turns a particular
drift into a collection-time crash instead.

**Proposed fix:** guard the subscription with an explicit lookup that raises a
descriptive `AssertionError` (mirroring `_extract_schema_fence`'s
`raise AssertionError(msg)` style) when the inline table is absent, e.g. "the
init document no longer carries `[drafting.critic].last_finding_counts` as an
inline table; update `_emitted_leaf_names`". This keeps the helper's drift
failure legible and consistent with the module's other not-found paths. Pure
test-robustness change, no behavioural effect on a passing run.

## 5. Leaf and header documented-checks restate a `re`-over-lines idiom

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`tests/test_state_layout_schema_guard.py`](../../tests/test_state_layout_schema_guard.py)
  `_leaf_is_documented` (lines 248-249), `_header_is_documented` (lines
  267-271), `_emitted_table_headers` (lines 99-104), and the inline header scan
  in `_chapters_block` (line 225).

Four helpers independently iterate `text.splitlines()`, `strip()` each line, and
match it against `_HEADER_LINE_RE` or a per-name leaf pattern. The header-line
recognition in particular is restated in three places (`_emitted_table_headers`,
`_header_is_documented`, and the `_chapters_block` boundary test), each doing
`_HEADER_LINE_RE.match(line.strip())`. The logic is small and correct, but the
"is this stripped line a `[header]`?" predicate exists in three spellings, so a
future change to the header grammar (for example admitting a quoted dotted key)
must be made in each. This is a within-module test-helper duplication, not a
production concern.

**Proposed fix:** none required at this size; the helpers are short and clear.
Recorded so that if the header/leaf grammar grows, a single
`_is_header_line(line) -> str | None` (returning the captured header or `None`)
and a single `_line_assigns(name, line) -> bool` are introduced and consumed by
all sites, rather than spreading a fourth copy of the `splitlines`/`strip`/match
idiom. No change is warranted for 2.1.8 alone.

## Pre-existing items not re-litigated

The chapter-manifest prose in `state-layout.md` ("Chapter manifest" section,
line 198) refers to "The `[chapters]` array" using single-bracket TOML table
syntax for what the schema fence correctly renders as the `[[chapters]]`
array-of-tables. This single-vs-double-bracket prose looseness predates 2.1.8
(the section is unchanged by this slice) and is cosmetic — the fence the guard
checks uses the correct `[[chapters]]` form — so it is noted for visibility only
and not raised as a 2.1.8 regression. No new roadmap item is proposed for it.
