# Reconcile state-layout.md with the emitted state schema

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DONE

## Purpose / big picture

`novel-state init` emits a `state.toml` whose schema the reference
documentation no longer describes faithfully. Beta testing surfaced two
specific drifts: the emitted document carries a top-level `chapters` array (an
empty `[[chapters]]` manifest) and a `[drafting.critic].convergence_target`
field, and neither is mentioned in
`skill/novel-ralph/references/state-layout.md`. That reference is the
**authoritative source** for the on-disk layout (design
`docs/novel-ralph-harness-design.md` §5.1, first paragraph), so a reader who
trusts it builds a wrong mental model of the shipped state.

After this change, a reader of `state-layout.md` sees both fields documented in
the schema, with the same semantics the typed schema and the design carry, and
a new automated guard fails `make test` if `init` ever emits **any** leaf key
(under any table) or table header that the reference does not document. The
guard is a true drift net over the whole emitted document, not a check of two
scopes: every emitted leaf name and every emitted table header must appear in
the documented fence, so a future undocumented field under `[gates.final]`,
`[word_counts]`, `[drafting.fangirl]`, or any other table fails the guard too
(roadmap success criterion "fails if the emitted schema drifts from the
reference again"; review round 1 blocking point B1). The drift that beta
testing found by hand becomes a test that cannot silently re-open.

The guard derives its required leaf and header sets from the **serialised
shape** of the `init` document — `tomlkit.dumps(build_initial_document(...))` —
not from a type-based walk of the in-memory document. This matters because
tomlkit's serialised form, not its in-memory object graph, is what the
documented fence must mirror, and the two diverge in two load-bearing ways
(both verified empirically in the worktree, round 4):

1. The parent-only table `gates` carries **no scalar leaves of its own** (only
   the sub-tables `knitting` and `final`), so `tomlkit.dumps` emits **no bare
   `[gates]` line** — only `[gates.knitting]` and `[gates.final]`. The fence
   correctly has no `[gates]` line either (state-layout.md lines 104-109), and
   design line 604 fixes the on-disk form as `[gates.knitting]`/
   `[gates.final]`, **never** `[gates]`. A type-based `isinstance(v, Table)`
   walk would wrongly demand a documented `[gates]` header, leaving that row
   RED-green-after.
2. The empty `chapters` array serialises as the bare leaf line `chapters = []`
   (identical in shape to `phase.completed`'s `completed = []`), **not** as a
   `[[chapters]]` table-array header. But the reference documents the
   *populated* manifest as a `[[chapters]]` block
   (number/slug/title/target_words), because an empty `chapters = []` teaches a
   reader nothing about the manifest fields (design §5.1). So `chapters` is the
   one emitted leaf the guard must **not** require as a `chapters =` line: it
   is documented as a table-array header block and its sub-fields are checked
   separately against `ChapterEntry`.

Deriving from the serialised dump makes both exceptions fall out automatically
and correctly for any future parent-only table, and removes the fragile,
empirically-wrong positional special-case the round-3 plan carried.

You can see success three ways:

1. Reading `skill/novel-ralph/references/state-layout.md`, the
   `## state.toml schema` TOML example shows a `[[chapters]]` manifest entry
   and a `convergence_target` line inside `[drafting.critic]`, and the prose
   explains both.
2. Running `make test` passes, and the new guard test
   `tests/test_state_layout_schema_guard.py::TestEmittedSchemaIsDocumented`
   fails before the documentation edit (specific failing rows named in work
   item 2's RED demonstration) and passes after.
3. Running `make markdownlint` and `make nixie` pass on the edited reference.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Do **not** edit any file in the root/control worktree. All work happens inside
  the worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-8`.
- Do **not** change the emitted schema. The emitter
  `novel_ralph_skill/state/initial.py` (`build_initial_document`) and the typed
  schema `novel_ralph_skill/state/schema.py` are correct and frozen for this
  task; this task reconciles the *documentation* and *adds a guard*, it does
  not alter behaviour. If the documentation and the emitter disagree on intent,
  the emitter and design §5.1 win, and the documentation is brought into line.
- Preserve the existing `state-layout.md` `toml` fence as the single schema
  example. Do not split it into multiple fences or convert it to a different
  language tag — the existing direct-write-recipe guard
  (`tests/_state_layout_scanner.py`, roadmap 1.2.8/7.3.3) treats `toml` fences
  as illustration-only, and that behaviour must remain.
- All prose, comments, and commit messages use en-GB Oxford spelling
  (`-ize`/`-yse`/`-our`) per `docs/documentation-style-guide.md` and AGENTS.md.
- The guard test lives under the top-level `tests/` tree, not inside the package
  (AGENTS.md "Keep pytest tests in the top-level `tests/` tree"), and reads the
  reference through the existing `read_repo_text` fixture (`tests/conftest.py`;
  developers-guide "Shared test scaffolding"), never by re-opening the file
  with its own reader.
- Keep every touched file under the 400-line cap (AGENTS.md "Keep file size
  manageable").

## Tolerances (exception triggers)

- Scope: if reconciliation requires changing more than `state-layout.md` plus
  one new test module (and optionally one tiny support helper), or more than
  roughly 250 net lines, stop and escalate — the task is documentation plus a
  guard, not a code change.
- Behaviour: if any change to `novel_ralph_skill/` runtime code (the emitter,
  the schema, the parser, any command) appears necessary, stop and escalate.
  This task must not alter emitted behaviour.
- Interface: if a public API signature in `novel_ralph_skill/state/__init__.py`
  must change, stop and escalate.
- Dependencies: if a new external dependency is required, stop and escalate. The
  guard uses only `tomlkit` (already locked, used by the emitter) and the
  standard library.
- Iterations: if the guard test still fails after 3 attempts to align it with
  the emitted shape, stop and escalate.
- Ambiguity: design §5.1 lists three added fields (`[chapters]`,
  `[drafting.critic].convergence_target`, and `[pending_turn]`), but the
  roadmap task names only the first two (the ones `init` emits). If it becomes
  unclear whether `[pending_turn]` must also be reconciled here, stop and
  present the options — see Risk "scope creep into `[pending_turn]`" and
  Decision Log D2.

## Risks

```plaintext
    - Risk: the documentation example diverges from the emitter in a way the
      textual guard cannot see (e.g. a key documented with the wrong nesting).
      Severity: medium
      Likelihood: medium
      Mitigation: the guard derives the *expected* leaf-key and table-header set
      from `tomlkit.dumps(build_initial_document(...))` at runtime — the
      serialised on-disk shape, so the required set is exactly the lines the
      reference must mirror — and asserts each emitted leaf name and table header
      is present in the documented fence, so a missing or undocumented key fails
      the test. The guard is a presence check over emitted-key names anchored to
      the fence's TOML syntax (leaf names asserted as a `name =` assignment line;
      tables as a `[header]`/`[[header]]` line), not a fuzzy substring match, so a
      stray prose mention cannot mask a missing fence entry (review round 1
      advisory A1).

    - Risk: the `state-layout.md` schema fence is not valid TOML (the
      `by_chapter = { "01" = 3200, ..., ... }` line uses a literal `...`
      placeholder), so a guard that tries to `tomllib.loads` the fence body
      crashes rather than asserting.
      Severity: medium
      Likelihood: high
      Mitigation: the guard does **not** parse the fence as TOML. It extracts the
      fenced block textually and checks that each emitted key path's leaf key (and
      its table header where applicable) appears as documented text. Decision Log
      D3 records this.

    - Risk: the emitted `chapters` array is **empty**, so a flattener over the
      `init` document yields the top-level key `chapters` but never the manifest
      sub-fields `number`/`slug`/`title`/`target_words` — those names live only
      in `ChapterEntry`/design §5.1, never in an `init` document.
      Severity: medium
      Likelihood: high (this is certain, not a possibility)
      Mitigation: the guard derives the chapter manifest sub-field names from
      `ChapterEntry`'s dataclass fields
      (`tuple(f.name for f in dataclasses.fields(ChapterEntry))`), **not** from
      the emitted document. This is drift-resistant against the schema (a new
      `ChapterEntry` field is picked up automatically) while remaining honest
      that the emitter gives the flattener nothing to traverse. Decision Log D4
      records the split: top-level and per-table leaf keys come from the emitter;
      chapter sub-fields come from `ChapterEntry`. Review round 1 blocking point
      B2.

    - Risk: a type-based walk of the in-memory `init` document derives a header
      or leaf set that the serialised fence cannot satisfy, so a parametrized row
      is RED-green-after and the guard can never ship. Two concrete cases,
      **both verified empirically in the worktree (round 4)**:
      (a) `gates` is a `tomlkit.items.Table` carrying only the sub-tables
      `knitting` and `final` and **no scalar leaf of its own**, so
      `tomlkit.dumps` emits **no bare `[gates]` line** — only `[gates.knitting]`
      and `[gates.final]`. An `isinstance(v, Table)` header walk yields `gates`
      as a required header, but the fence (correctly) has no `[gates]` line and
      design line 604 fixes the form as `[gates.knitting]`/`[gates.final]`, never
      `[gates]`. So `test_every_emitted_table_header_is_documented[gates]` would
      stay RED-green-after. (b) the empty `chapters` array serialises as the bare
      leaf line `chapters = []`, **not** as a `[[chapters]]` header, yet the
      reference documents the manifest as a `[[chapters]]` block; a leaf net that
      required a `chapters =` line would stay RED-green-after too.
      Severity: high
      Likelihood: high (this is certain, not a possibility — verified by running
      `tomlkit.dumps(build_initial_document(...))` in the worktree: the only
      header lines emitted are `[novel]`, `[phase]`, `[drafting]`,
      `[drafting.critic]`, `[drafting.fangirl]`, `[gates.knitting]`,
      `[gates.final]`, `[word_counts]` — `gates` and `chapters` both absent as
      headers — and the only top-level array lines are `chapters = []` and, under
      `[phase]`, `completed = []`)
      Mitigation: the guard derives **both** the header net and the leaf net from
      the **serialised dump** `tomlkit.dumps(build_initial_document(...))`, not
      from a type-based walk. The header net is the set of distinct
      `[header]`/`[[header]]` lines the dump emits, so parent-only tables like
      `gates` are excluded automatically and correctly (and any future
      parent-only table is handled with no special-case). The leaf net is the
      set of `name =` assignment lines the dump emits, which includes
      `chapters = []` and `completed = []`; the single emitted leaf `chapters`
      is then excluded from the required-leaf set by a named, design-justified
      exception (it is documented as the `[[chapters]]` manifest block, not a
      `chapters =` scalar, and its sub-fields are checked separately against
      `ChapterEntry`). This is the PREFERRED fix in review round 3 blocking point
      B-R3.1: the header net is drift-correct for every parent-only table, and the
      `chapters` leaf exception is the *only* leaf exception, justified by the
      design's chosen rendering. Decision Log D5 (corrected) and D6, and work
      item 2 helper point 2, state the exact rule.

    - Risk: `test_chapters_manifest_is_documented` checks the four
      `ChapterEntry` field names against the **whole** `## state.toml schema`
      fence rather than the `[[chapters]]` example block. Because `slug` and
      `title` already appear under `[novel]` (fence lines 67-68), a
      whole-fence presence check passes for those two even if the implementer
      forgets to put them inside the `[[chapters]]` example — a false negative
      that defeats the test's stated purpose (only the unique names `number` and
      `target_words` would be genuinely exercised).
      Severity: medium
      Likelihood: medium
      Mitigation: the test first extracts the `[[chapters]]` sub-block (from the
      `[[chapters]]` header line up to the next table header or the end of the
      fence) and runs the four-field presence check against **that sub-block**,
      not the whole fence. So all four fields — including the shared `slug` and
      `title` — must actually appear inside the documented `[[chapters]]` entry.
      Work item 2 helper point 5 and test 2 state the sub-block extraction.
      Review round 2 blocking point B-R2.2.

    - Risk: name-only leaf presence is table-blind, so a single documented
      `current =` line satisfies the emitted `current` under both `[phase]` and
      `[word_counts]`, and a single `title`/`slug` line is shared by `[novel]`
      and (in the manifest check) `ChapterEntry`.
      Severity: low
      Likelihood: low
      Mitigation: accepted as a deliberate, documented limitation of a
      name-presence net — a genuinely new emitted leaf name is overwhelmingly
      likely to be unique, so the masking risk is negligible. The plan states
      this honestly rather than implying per-occurrence coverage; the
      `[[chapters]]` sub-block extraction (B-R2.2 fix) restores per-occurrence
      coverage for the one place it matters (the manifest fields). Review round 2
      advisory A-R2.1.

    - Risk: a leaf-name presence check could pass on a coincidental match (a leaf
      name that also appears as prose or as a different table's text) and so miss
      a genuinely undocumented field.
      Severity: low
      Likelihood: low
      Mitigation: assert each emitted leaf name against a `name =` assignment
      line *inside the extracted fence* (a small per-leaf regex anchored on the
      key followed by optional whitespace and `=`), not a bare substring over the
      whole document. Every currently emitted leaf name already appears as such a
      line in the fence except `convergence_target` (added by item 1), so the
      generalised guard goes green exactly when item 1 lands and red otherwise
      (verified: see "Surprises & discoveries"). Review round 1 advisory A1.

    - Risk: scope creep into `[pending_turn]`. Design §5.1 lists `[pending_turn]`
      as a third added field, but `init` never emits it, so the roadmap excludes
      it.
      Severity: low
      Likelihood: medium
      Mitigation: the guard is scoped to *what `init` emits*. `[pending_turn]` is
      out of scope for the guard (it is never in an `init` document) and out of
      scope for the documentation edit unless escalated. Decision Log D2.

    - Risk: the existing direct-write-recipe guard's `toml`-fence
      illustration-only rule is disturbed by editing the fence.
      Severity: low
      Likelihood: low
      Mitigation: the edit only adds lines inside the existing `toml` fence; it
      adds no executable fence and names no write primitive. Re-run the full suite
      (which includes `tests/test_state_layout_reference.py`) to confirm.

    - Risk: markdownlint or nixie fails on the edited reference (line length,
      fenced-code rules).
      Severity: low
      Likelihood: medium
      Mitigation: run `make markdownlint` and `make nixie` as part of the work
      item's validation, and `make fmt` to auto-format Markdown before linting.
```

## Progress

```plaintext
    - [x] Work item 1: Document `chapters` and `convergence_target` in
      `state-layout.md` (the failing-then-passing documentation edit).
      Completed 2026-06-25: added the `convergence_target = 1` line to
      `[drafting.critic]`, a `[[chapters]]` manifest example after
      `[word_counts]`, a `convergence_target` sentence in "### Critic sub-state",
      and a new "### Chapter manifest" subsection. `markdownlint-cli2` on the
      edited file and `make nixie` both pass. The `## Initialisation` list needed
      no change — it lists no exhaustive schema and does not contradict
      `chapters = []`/`convergence_target`.
    - [x] Work item 2: Add the emitted-schema-drift guard test (a full-leaf
      drift net over every emitted leaf and table header, with chapter sub-fields
      derived from `ChapterEntry`).
      Completed 2026-06-25: added `tests/test_state_layout_schema_guard.py` with
      `class TestEmittedSchemaIsDocumented` (two scalar pins plus two
      parametrized nets over the dump-derived `emitted_table_headers` and
      `emitted_leaf_names`). The leaf net derives from
      `tomlkit.dumps(build_initial_document(...))` plus the inline
      `last_finding_counts` inner keys, with `chapters` excluded (D6). The RED
      demonstration on the pre-item-1 reference reddened exactly the three named
      rows; the documented reference greens all 35 rows. `make all` and
      `make audit` both pass at exit 0.

(Timestamps added as work proceeds. Plan revised 2026-06-25 round 2 to resolve
review blocking points B1/B2/B3, then round 3 to resolve B-R2.1/B-R2.2 and fold
in advisories A-R2.1/A-R2.2/A-R2.3, then round 4 to resolve B-R3.1 by deriving
the header and leaf nets from the serialised dump (`tomlkit.dumps`) rather than
a type walk — see Revision note.)
```

## Surprises & discoveries

```plaintext
    - Observation: a guard module already exists for `state-layout.md`
      (`tests/test_state_layout_reference.py` + `tests/_state_layout_scanner.py`),
      but it guards against direct-*write* recipes, not schema *drift*. It is the
      wrong guard for this task.
      Evidence: read both files; their docstrings cite ADR-002 and design §4.1
      (the no-direct-edit rule), not §5.1 (the schema).
      Impact: this task adds a *new, separate* guard rather than extending the
      write-recipe scanner; conflating the two would muddy both concerns.

    - Observation: in the **serialised** `init` dump
      (`tomlkit.dumps(build_initial_document(...))`), every emitted leaf name
      **except** `convergence_target` already appears in the shipped fence as a
      `name =` line, and every emitted **header** line already appears in the
      fence. The full-leaf guard therefore reddens on exactly the one
      undocumented leaf (`convergence_target`) plus the separately-checked
      `[[chapters]]` manifest, and greens precisely when item 1 lands.
      Evidence: running `tomlkit.dumps(build_initial_document(title="T", slug="s",
      target_word_count=80000, created_at="…"))` in the worktree (round 4) prints
      these and only these header lines — `[novel]`, `[phase]`, `[drafting]`,
      `[drafting.critic]`, `[drafting.fangirl]`, `[gates.knitting]`,
      `[gates.final]`, `[word_counts]` — and these `name =` leaf lines:
      `schema_version`, `chapters` (as `chapters = []`),
      `novel.{title,slug,target_word_count,created_at}`,
      `phase.{current,completed}` (`completed = []`),
      `drafting.{current_chapter,current_scene,current_beat}`,
      `drafting.critic.{pass,consecutive_clean,convergence_target,
      last_finding_counts}` (the inline-table leaves
      `blocker`/`major`/`minor`/`taste`),
      `drafting.fangirl.last_chapter_passed`,
      `gates.knitting.{done_30,done_50,done_80}`,
      `gates.final.final_pass_complete`,
      `word_counts.{target,current,by_chapter}`. Cross-reading the fence in
      `state-layout.md` (lines 63-116) confirms every header line and every leaf
      name appears save `convergence_target` (added by item 1). The single
      emitted leaf `chapters` is deliberately **excluded** from the required-leaf
      set (it is documented as the `[[chapters]]` block, item 1; see D6). The
      implementer must re-confirm this with the RED run rather than trusting the
      prose.
      Impact: the generalised B1 guard is not just safe but *required* to bite —
      it costs nothing extra over the two-scope version and turns a future
      undocumented `[gates.final]`/`[word_counts]` leaf into a test failure.

    - Observation: `gates` is the **only** parent table that emits no bare header
      line, because it carries no scalar leaf of its own (only the sub-tables
      `knitting` and `final`). Every other parent table — `novel`, `phase`,
      `drafting`, `word_counts` — carries scalar leaves and so serialises a bare
      `[header]` line. The round-3 plan's claim "every table header appears save
      `[[chapters]]`" and its earlier framing that `chapters` is "the only"
      exception were both **factually wrong**: there is a second exception
      (`gates`), and `chapters` is not even a header in the emitted dump.
      Evidence: `tomlkit.dumps(build_initial_document(...))` in the worktree
      (round 4) emits `[gates.knitting]` and `[gates.final]` but **no** `[gates]`
      line; an `isinstance(v, Table)` walk would, by contrast, yield `gates` as a
      header (`type(doc["gates"])` is `tomlkit.items.Table` with keys
      `["knitting", "final"]`). Design line 604 fixes the on-disk form as
      `[gates.knitting]`/`[gates.final]`, never `[gates]`.
      Impact: the header net is derived from the serialised dump's header lines,
      not a type walk, so `gates` (and any future parent-only table) is excluded
      automatically and correctly. Do **not** add a bare `[gates]` line to the
      fence — that would contradict design line 604. Decision Log D5 (corrected)
      and work item 2 helper point 2 state the rule. Review round 3 blocking
      point B-R3.1.

    - Observation: the empty `chapters` array and the empty `phase.completed`
      array **both serialise as bare leaf lines** — `chapters = []` (top level)
      and `completed = []` (under `[phase]`) — **not** as `[[chapters]]` or
      `[[completed]]` headers. The round-3 plan's premise that `chapters` emits a
      `[[chapters]]` table-array header was **factually wrong**: an empty
      `tomlkit.array()` always dumps as `key = []`.
      Evidence: `tomlkit.dumps(build_initial_document(...))` in the worktree
      (round 4) shows the line `chapters = []` at the top of the document and
      `completed = []` under `[phase]`; `type(doc["chapters"])` and
      `type(doc["phase"]["completed"])` are both `tomlkit.items.Array`.
      Impact: in the leaf net, `chapters` is the **single** named exception — it
      is excluded from the required-leaf set because the reference documents the
      *populated* manifest as a `[[chapters]]` block (an empty `chapters = []`
      would teach nothing), and its sub-fields are checked separately against
      `ChapterEntry`. `completed` stays a required leaf (it is documented as a
      `completed =` line). Decision Log D6; work item 2 helper point 2.

    - Observation: `last_finding_counts` (emitter line 96) and `by_chapter`
      (emitter line 133) are `InlineTable`s, and both appear as `name = {` lines
      in the fence (`state-layout.md` lines 93 and 115); `slug` and `title`
      appear under `[novel]` (fence lines 67-68), so a whole-fence check of the
      manifest fields would pass for `slug`/`title` even if they were omitted
      from the `[[chapters]]` example.
      Evidence: read the emitter and the fence directly (round 3).
      Impact: `test_chapters_manifest_is_documented` extracts the `[[chapters]]`
      sub-block and checks the four fields against it, not the whole fence
      (Decision Log via B-R2.2; work item 2 helper point 5, test 2).

    - Observation: `ChapterEntry`'s four fields are `number`, `slug`, `title`,
      `target_words` (in that declaration order).
      Evidence: `novel_ralph_skill/state/schema.py` lines 89-92.
      Impact: `tuple(f.name for f in dataclasses.fields(ChapterEntry))` yields
      exactly those four names for the manifest check (point 4).
```

## Decision log

```plaintext
    - Decision: D1 — scope the change to documentation plus a new guard test; do
      not touch runtime code.
      Rationale: the roadmap task and design §5.1 treat the emitter as correct and
      the reference as drifted. "Reconcile" means bring the reference to the
      emitter, not the reverse.
      Date/Author: 2026-06-25, planning agent.

    - Decision: D2 — reconcile only `chapters` and `convergence_target`; treat
      `[pending_turn]` as out of scope.
      Rationale: the roadmap task names exactly those two fields ("both absent
      from … state-layout.md"), and they are exactly the two `init` emits beyond
      the documented reference structure. `[pending_turn]` is never in an `init`
      document, so the emitted-drift guard cannot and should not require it. If a
      reviewer wants `[pending_turn]` documented too, that is a follow-up.
      Date/Author: 2026-06-25, planning agent.

    - Decision: D3 — the guard checks documented-key *presence* textually against
      the fenced schema block; it does not parse the fence as TOML.
      Rationale: the reference's `by_chapter` line carries a literal `...`
      ellipsis placeholder, so the fence is intentionally not valid TOML. The
      expected key set is derived by flattening `build_initial_document`'s output
      (which *is* a real `tomlkit` document); the documented fence is the human
      text the keys must appear in.
      Date/Author: 2026-06-25, planning agent.

    - Decision: D4 — derive the expected top-level **and every per-table leaf
      key** from `build_initial_document`; derive the chapter manifest sub-fields
      from `ChapterEntry` because `init` emits an **empty** `chapters` array.
      Rationale: a hand-written list would itself drift. Deriving from the emitter
      means the guard tracks whatever `init` actually emits, so a future leaf
      under *any* table (not only top-level tables or `[drafting.critic]`) added
      to the emitter without being documented fails the guard automatically —
      this is the full drift net the roadmap asks for (review round 1 B1). The
      one place the emitter cannot supply names is the chapter manifest: the
      emitted `chapters` array is empty (length 0; verified empirically in review
      round 1), so a flattener over the `init` document yields the top-level key
      `chapters` but cannot yield `number`/`slug`/`title`/`target_words`. Those
      four names are therefore derived from
      `dataclasses.fields(ChapterEntry)` — drift-resistant against the schema
      and honest about the empty-array constraint — not from the emitted document
      and not from a bare string literal (review round 1 B2). The earlier framing
      of D4 ("derive everything from the emitter") was a contradiction for the
      chapter fields and is corrected here.
      Date/Author: 2026-06-25, planning agent (revised round 2).

    - Decision: D5 — derive **both** the header net and the leaf net from the
      **serialised dump** `tomlkit.dumps(build_initial_document(...))`, not from
      a type-based walk of the in-memory document. `emitted_table_headers` is the
      set of distinct `[header]`/`[[header]]` lines the dump emits;
      `emitted_leaf_names` is the set of `key` names from `key = …` assignment
      lines the dump emits.
      Rationale: the serialised dump is exactly the textual shape the documented
      fence must mirror, so requiring a documented line for each *emitted line* is
      drift-correct by construction. A type-based walk diverges from the dump in
      two empirically-verified ways that each leave a parametrized row
      RED-green-after (round 4): (1) `gates` is a `tomlkit.items.Table` carrying
      only sub-tables, so a type walk yields `gates` as a header, but the dump
      emits no `[gates]` line and the fence correctly has none (design line 604
      fixes the form as `[gates.knitting]`/`[gates.final]`, never `[gates]`); (2)
      the empty `chapters` array is a `tomlkit.items.Array` that a type walk might
      treat as a table-array header, but the dump emits it as the bare leaf line
      `chapters = []`. Deriving from the dump makes `gates` (and every future
      parent-only table) fall out of the header net automatically with no
      special-case, replacing the round-3 positional special-case — which was
      built on the false premise that `chapters` emits a `[[chapters]]` header and
      that `gates` was not an exception. The header net needs **no** exceptions;
      the only exception lives in the leaf net (D6). Review round 3 blocking point
      B-R3.1, PREFERRED fix.
      Date/Author: 2026-06-25, planning agent (corrected round 4).

    - Decision: D6 — the single emitted leaf `chapters` (serialised as
      `chapters = []`) is the **only** name excluded from the required-leaf set.
      The leaf net derived from the dump (D5) includes `chapters`, but the guard
      drops it before asserting, because the reference documents the *populated*
      manifest as a `[[chapters]]` table-array block (number/slug/title/
      target_words), not as a `chapters =` scalar. The manifest's presence and
      sub-fields are checked separately by `test_chapters_manifest_is_documented`
      against `dataclasses.fields(ChapterEntry)` (D4).
      Rationale: an empty `chapters = []` line teaches a reader nothing about the
      manifest, so the design (§5.1) and the reference document the field as a
      populated `[[chapters]]` example. Requiring a `chapters =` leaf line would
      contradict that documented rendering and leave
      `test_every_emitted_leaf_is_documented[chapters]` RED-green-after. The
      exclusion is named and minimal: it is the *one* leaf the design renders as a
      block rather than a scalar, and `phase.completed` — also an empty array,
      also serialised as `completed = []` — stays a required leaf because it is
      documented as a `completed = […]` line. This exclusion is the leaf-net
      counterpart of the header net's automatic exclusion of `gates`; together
      they are the complete set of emitted-vs-documented shape mismatches, both
      justified by the design's chosen rendering. Review round 3 blocking point
      B-R3.1.
      Date/Author: 2026-06-25, planning agent (added round 4).
```

## Outcomes & retrospective

Both work items landed as planned, in order, each as one atomic commit gated by
`make all` (plus `make markdownlint`/`make nixie` for the Markdown edit).

- The round-4 serialised-dump model held exactly: the dump emits eight header
  lines (no `[gates]`, no `[chapters]`) and the leaf net (with the inline
  `last_finding_counts` inner keys folded in and `chapters` excluded) matched
  the documented fence save `convergence_target` before item 1, greening
  precisely when item 1 landed. No deviation from D5/D6 was needed.
- No runtime `novel_ralph_skill/` code changed; the task stayed within its
  documentation-plus-guard tolerance (one edited reference plus one new test
  module, well under 250 net lines and the 400-line file cap — the guard module
  is ~330 lines).
- Deviation from the literal Concrete-steps RED recipe: because item 1 is
  committed (so the reference is clean at HEAD), the RED check exercised the
  guard predicates against `git show HEAD~1:…/state-layout.md` rather than a
  `git stash` of an uncommitted edit. The outcome is identical — the three named
  rows red on the reverted reference — and the worktree's repository-wide
  `git stash`/`git restore` safety net made the swap-in-place form impractical.
  Recorded here for the next agent.
- A repo-wide hazard worth signposting: `make fmt` runs `mdformat-all`, which
  reflows every Markdown file in the tree and introduces mass MD013 churn
  unrelated to the task (matching the long history of "spurious make-fmt
  mdformat churn" stashes). That churn was parked in a `git stash` and only the
  intentional `state-layout.md` edit was kept; `markdownlint-cli2` was run
  directly on the edited file (0 errors). Do not `make fmt` and commit the
  result blindly.

## Context and orientation

You are working in a Python skill package, `novel_ralph_skill`, that ships a
set of console scripts (`novel-state`, `novel-compile`, …) plus a skill
reference directory under `skill/novel-ralph/`. The harness keeps all of its
memory on disk in `working/state.toml`; the typed shape of that file is the
project's "state schema".

The files that matter for this task, by full repository-relative path within
the worktree:

- `skill/novel-ralph/references/state-layout.md` — the authoritative on-disk
  layout reference. Its `## state.toml schema` section holds a single
  ```` ```toml ```` fenced example, followed by prose subsections ("### Critic
  sub-state", "### Gates", …). **This is the file to edit.** As shipped, the
  fence shows `[novel]`, `[phase]`, `[drafting]`, `[drafting.critic]` (with
  `pass`, `consecutive_clean`, `last_finding_counts`), `[drafting.fangirl]`,
  `[gates.knitting]`, `[gates.final]`, and `[word_counts]`. It does **not**
  show a `[[chapters]]` entry and does **not** show `convergence_target`.

- `novel_ralph_skill/state/initial.py` —
  `build_initial_document(*, title, slug, target_word_count, created_at) -> tomlkit.TOMLDocument`.
  This is the emitter.
  Reading it confirms the emitted shape:
  `document["chapters"] = tomlkit.array()` (a top-level empty array that
  serialises as the bare leaf line `chapters = []`, not as a `[[chapters]]`
  header — see Decision Log D6) and, in `_drafting_table`,
  `critic["convergence_target"] = _DEFAULT_CONVERGENCE_TARGET` (the literal
  `1`).

- `novel_ralph_skill/state/schema.py` — the frozen typed dataclasses mirroring
  the schema. `CriticState.convergence_target: int` (with the docstring "the
  configured ceiling for `consecutive_clean` (default 1)") and
  `State.chapters: tuple[ChapterEntry, ...]` (the manifest, "ordered ascending
  by `number`") are the canonical semantics the documentation must match.
  `ChapterEntry` carries `number: int`, `slug: str`, `title: str`,
  `target_words: int` — the guard reads these four names from
  `dataclasses.fields(ChapterEntry)` because `init` emits an empty `chapters`
  array (Decision Log D4).

- `docs/novel-ralph-harness-design.md` §5.1 ("Schema") — the design rationale.
  It states `state-layout.md` "is the authoritative source for the on-disk
  layout, and the design follows it exactly", then says "The validated schema
  adds three fields beyond the reference structure": `[chapters]` (the
  manifest, number/slug/title/target words, written by `set-chapters`),
  `[drafting.critic].convergence_target` ("the configured ceiling for
  `consecutive_clean` (default 1), replacing the hard-coded literal"), and
  `[pending_turn]`. This task closes the gap between "adds beyond the
  reference" and "the reference is authoritative" for the two fields `init`
  emits.

- `tests/conftest.py` — provides the `read_repo_text` fixture (a
  `RepoTextReader` protocol callable that reads a repo-relative file as UTF-8)
  and the `project_root` fixture. The guard test consumes `read_repo_text`; the
  `RepoTextReader` type may be imported from `conftest` under
  `if TYPE_CHECKING:` (developers-guide "Shared test scaffolding").

- `tests/test_state_layout_reference.py` + `tests/_state_layout_scanner.py` —
  the
  *existing* `state-layout.md` guard. It forbids direct-write recipes (ADR-002,
  design §4.1). It is **not** the guard this task needs; this task adds a
  separate schema-drift guard. Read it only to confirm the new guard does not
  duplicate or disturb it, and to mirror its house style for reading the
  reference through `read_repo_text`.

- `tests/test_state_schema.py` — the parse tests for the typed schema. It
  already
  exercises a non-default `convergence_target` (the `_two_chapter_spec` helper
  sets `convergence_target=2`) and the `[chapters]` manifest. Read it to
  confirm the emitted-key vocabulary (`convergence_target`, `chapters`,
  `number`, `slug`, `title`, `target_words`) and to avoid re-testing parser
  behaviour the new guard does not own.

Terms used in this plan:

- **Emitted schema**: the set of TOML key paths present in the document
  `build_initial_document` returns (e.g. `schema_version`, `novel.title`,
  `drafting.critic.convergence_target`, `chapters`).
- **Documented schema**: the keys shown in the ```` ```toml ```` fenced example
  under `## state.toml schema` in `state-layout.md`.
- **Drift**: a key path in the emitted schema that does not appear in the
  documented schema (the failure the guard catches).
- **Guard test**: a `pytest` test that fails when drift exists, so the reference
  cannot silently fall out of sync with `init` again.

## Plan of work

The work is two atomic, independently committable items, ordered so the guard
is written against an already-correct reference. Test-driven order: write the
*documentation* first as the behaviour change, then add the *guard* that locks
it in. (The guard is a regression net, so it is added second; each item is
gate- passable on its own.)

Standard preamble for both items — change directory into the worktree, then
load the Python router skill before touching any Python:

- Working directory:
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-8`.
- Load `python-router`; it routes the guard-test work to `python-testing`
  (pytest fixtures, the `read_repo_text` boundary) and, for the key-flattening
  helper, `python-iterators-and-generators`. No property or symbolic-execution
  adversary is warranted here — the guard asserts a fixed set membership over a
  small deterministic document, so `hypothesis`/`crosshair`/`mutmut` are not
  required (escalate only if review asks for a generated drift corpus).

### Work item 1 — Document `chapters` and `convergence_target`

Documentation to read first:

- `docs/novel-ralph-harness-design.md` §5.1 (the three added fields and their
  semantics — this is the wording to mirror).
- `skill/novel-ralph/references/state-layout.md` `## state.toml schema` and its
  "### Critic sub-state" and "### Gates" prose subsections (the surrounding
  style to match).
- `docs/documentation-style-guide.md` (Oxford spelling, Oxford comma, heading
  and fenced-code conventions).
- `novel_ralph_skill/state/schema.py` `CriticState`, `ChapterEntry`,
  `State.chapters` (the canonical semantics and field names).

Skills to load: none beyond the standing docs/style rules; this item edits
Markdown only. (Load `en-gb-oxendict` if unsure about a spelling.)

Edits to `skill/novel-ralph/references/state-layout.md`:

1. Inside the existing ```` ```toml ```` fence under `## state.toml schema`,
   add a
   `convergence_target` line to the `[drafting.critic]` table, between
   `consecutive_clean` and `last_finding_counts`, with an inline comment
   matching the emitter and design (default ceiling for `consecutive_clean`).
   Mirror the emitter's value (`1`) and the design's phrase "configured ceiling
   for `consecutive_clean` (default 1)".

2. Inside the same fence, add a `[[chapters]]` manifest example after
   `[word_counts]` (or in the position that reads most naturally relative to
   the existing tables), showing the four fields `number`, `slug`, `title`,
   `target_words` with representative values, and a comment noting it is the
   ordered chapter manifest written by `novel-state set-chapters` (design §5.1;
   ADR-008), not by a direct edit. Keep the fence valid as illustration; the
   `by_chapter` ellipsis placeholder already establishes that the fence is
   illustrative, so a single representative `[[chapters]]` entry is sufficient.
   Keep the manifest comment short: fenced-code lines are governed by MD013
   `code_block_line_length: 120` (`.markdownlint-cli2.jsonc`), and aligning a
   long inline comment past column 120 trips markdownlint. Prefer a brief
   trailing comment (or a comment on its own line above the table) so the
   `[[chapters]]` lines stay well inside 120 columns (review round 2 advisory
   A-R2.3).

3. Add prose. Extend the "### Critic sub-state" subsection with a sentence
   defining `convergence_target` (the configured ceiling for
   `consecutive_clean`, default 1, replacing the previously hard-coded
   literal). Add a short "### Chapter manifest" subsection (or fold into an
   existing nearby subsection if that reads better) defining the `[chapters]`
   array: an ordered record of each planned chapter (number, slug, title,
   target words), the authoritative set `novel-state check` validates on-disk
   chapter directories against, written only by `novel-state set-chapters` per
   ADR-001/ADR-008. Cite design §5.1.

4. Reconcile the existing `## Initialisation` numbered list if it implies a
   schema that omits these fields — confirm it does not contradict an `init`
   document that now carries `chapters = []` and `convergence_target`. (Most
   likely no change is needed; verify and note in Progress.)

Validation for item 1:

- `make markdownlint` — expect pass (no MD errors on the edited file). Run
  `make fmt` first to auto-format Markdown.
- `make nixie` — expect pass (the reference carries no Mermaid diagrams, but the
  repo gate runs it for any `.md` change; confirm it is clean).
- Because item 2's guard is not yet present, the acceptance for item 1 in
  isolation is human-readable: the fence and prose now show both fields. The
  red-before/green-after demonstration of the *guard* belongs to item 2, where
  the order is deliberately: confirm the guard fails on a *reverted* reference,
  then passes on the documented one (see item 2's validation).

Commit item 1 alone once `make markdownlint` and `make nixie` pass.

### Work item 2 — Add the emitted-schema-drift guard test

Documentation to read first:

- AGENTS.md "Python verification and testing" and "Snapshot tests" rules (this
  guard is an assertion test, not a snapshot — keep it a direct assertion).
- `docs/developers-guide.md` "Shared test scaffolding" (the `read_repo_text`
  fixture and the `TYPE_CHECKING` import carve-out for `RepoTextReader`).
- `tests/test_state_layout_reference.py` (the house style for reading the
  reference through `read_repo_text` and the `_STATE_LAYOUT_PARTS` parts tuple
  to reuse the same path-addressing idiom).

Skills to load: `python-router` → `python-testing` (fixture wiring, the
`read_repo_text` boundary, parametrization over emitted key paths) and
`python-iterators-and-generators` (the line-scan over the serialised dump that
yields header and leaf names is naturally a generator over `dump.splitlines()`).

New file `tests/test_state_layout_schema_guard.py`:

- Import `build_initial_document` from `novel_ralph_skill.state` (it is exported
  there — confirmed in `novel_ralph_skill/state/__init__.py`).
- Consume the `read_repo_text` fixture; address the reference via the same parts
  tuple `("skill", "novel-ralph", "references", "state-layout.md")`.
- Implement a small pure helper (inline in the test module, or a tiny
  `tests/_state_schema_keys.py` support module if the test module would
  otherwise approach the 400-line cap — prefer inline) that:
  1. Builds a representative document via `build_initial_document(title="T",
     slug="s", target_word_count=80000, created_at="2026-01-01T00:00:00Z")` and
     **serialises it** with `tomlkit.dumps(...)` into the on-disk text the
     documented fence must mirror (Decision Log D5).
  2. **Derives two sets from the serialised dump text** (the B1 drift net, not a
     two-scope subset, and not a type-based walk of the in-memory document —
     Decision Log D5; review round 3 B-R3.1). Iterate the dump's lines and
     classify each by a small regex, mirroring the way TOML renders:
     - A line matching `^\[\[?(<dotted-header>)\]\]?\s*$` contributes
       `<dotted-header>` to `emitted_table_headers`. For the `init` dump this is
       exactly `novel`, `phase`, `drafting`, `drafting.critic`,
       `drafting.fangirl`, `gates.knitting`, `gates.final`, `word_counts`.
       **`gates` is absent** — it is a parent-only table carrying no scalar leaf,
       so tomlkit emits no bare `[gates]` line (verified round 4; design line 604
       fixes the form as `[gates.knitting]`/`[gates.final]`, never `[gates]`).
       The serialised derivation excludes it automatically, with no special-case,
       and would likewise exclude any future parent-only table. **`chapters` is
       absent from the header set** too — the empty array emits `chapters = []`,
       a leaf line, not a `[[chapters]]` header.
     - A line matching `^(<key>)\s*=` (a `key = …` assignment at the start of a
       line, after stripping indentation) contributes `<key>` to
       `emitted_leaf_names`. For the `init` dump this is `schema_version`,
       `chapters` (from `chapters = []`), `title`, `slug`, `target_word_count`,
       `created_at`, `current`, `completed` (from `completed = []`),
       `current_chapter`, `current_scene`, `current_beat`, `pass`,
       `consecutive_clean`, `convergence_target`, `last_finding_counts`,
       `last_chapter_passed`, `done_30`, `done_50`, `done_80`,
       `final_pass_complete`, `target`, `by_chapter`. (The inline-table contents
       `blocker`/`major`/`minor`/`taste` live on the same physical line as
       `last_finding_counts = {…}` and are *not* separate `key =` lines in the
       dump; they are matched in the fence as a courtesy by test 5's parametrize
       list, which is built from the names below — see the next paragraph for how
       the inline leaves are obtained.)
     - **Inline-table inner leaves.** `last_finding_counts` serialises inline
       (`last_finding_counts = {blocker = 0, …}`), so its inner names do not
       appear as their own `key =` lines in the dump. Obtain them by reading the
       in-memory inline table's keys
       (`tuple(doc["drafting"]["critic"]["last_finding_counts"].keys())` →
       `("blocker", "major", "minor", "taste")`) and add them to
       `emitted_leaf_names`. The empty `by_chapter` inline table contributes
       none. This is the one place the in-memory document supplements the dump,
       and it is type-stable (inline tables expose `.keys()`); it adds names the
       dump genuinely emits, just packed onto one line.
     - **The leaf exception (Decision Log D6).** Remove the single name
       `chapters` from `emitted_leaf_names` before asserting: the reference
       documents the *populated* manifest as a `[[chapters]]` block, not a
       `chapters =` scalar, so requiring a `chapters =` line would be
       RED-green-after. `completed` is **not** removed — it is documented as a
       `completed = […]` line. This is the only leaf exclusion.

     For the `init` document this yields the header set `novel`, `phase`,
     `drafting`, `drafting.critic`, `drafting.fangirl`, `gates.knitting`,
     `gates.final`, `word_counts` (note: **no** `gates`, **no** `chapters`), and
     the leaf set `schema_version`, `title`, `slug`, `target_word_count`,
     `created_at`, `current`, `completed`, `current_chapter`, `current_scene`,
     `current_beat`, `pass`, `consecutive_clean`, `convergence_target`,
     `last_finding_counts`, `blocker`, `major`, `minor`, `taste`,
     `last_chapter_passed`, `done_30`, `done_50`, `done_80`,
     `final_pass_complete`, `target`, `by_chapter` (note: **no** `chapters`,
     which is excluded by D6 and checked separately as the manifest).

     Limitation (stated honestly, review round 2 advisory A-R2.1): the leaf net
     is keyed on the leaf *name*, not the `(table, name)` pair, so it is
     table-blind. `current` is emitted under both `[phase]` and `[word_counts]`;
     one documented `current =` line satisfies both rows. `title`/`slug` are
     shared by `[novel]` and the manifest. This is an accepted limitation: a
     genuinely new emitted leaf name is overwhelmingly likely to be unique, so
     the masking risk is negligible. The one place per-occurrence coverage
     matters — the manifest fields — is restored by the `[[chapters]]`
     sub-block extraction in point 5 / test 2.
  3. Extracts the ```` ```toml ```` fenced block under `## state.toml schema`
     from the reference text (a small regex over the fence, matching the existing
     scanner's fence idiom; do **not** import the write-recipe scanner — that is
     a different concern, Decision Log notes the separation).
  4. Derives the chapter manifest sub-field names from `ChapterEntry`, **not**
     from the emitted document, because `init` emits an empty `chapters` array
     (Decision Log D4; review round 1 B2):
     `tuple(f.name for f in dataclasses.fields(ChapterEntry))` →
     `("number", "slug", "title", "target_words")`. Keeping this dataclass-derived
     means a future `ChapterEntry` field is required to be documented too.
  5. Provides three fence-anchored helpers over the extracted fence text
     (advisory A1; B-R2.2):
     - `_leaf_is_documented(name)` matches a `name =` assignment line (the key,
       optional whitespace, then `=`) anywhere in the extracted fence.
     - `_header_is_documented(header)` matches a `[header]` or `[[header]]` line
       in the extracted fence.
     - `_chapters_block(fence_text) -> str` extracts the `[[chapters]]`
       sub-block: the lines from the `[[chapters]]` header line up to (but not
       including) the next table header line (`[…]` or `[[…]]`) or the end of
       the fence, whichever comes first. The four manifest-field presence checks
       run against this sub-block via `_leaf_is_documented` applied to the
       sub-block string (not the whole fence), so `slug`/`title` — which also
       appear under `[novel]` — must genuinely appear *inside* the `[[chapters]]`
       example. This is the B-R2.2 fix: a whole-fence check would pass for
       `slug`/`title` even if the implementer omitted them from the manifest
       example.
     All three operate on the extracted fence (or its `[[chapters]]` sub-block)
     only, so a stray prose mention elsewhere in the document cannot satisfy
     them.

- Tests in a `TestEmittedSchemaIsDocumented` class:
  1. `test_convergence_target_is_documented` — assert `convergence_target` is
     documented as a `name =` line in the extracted fence. A named regression pin
     for the field the emitter sets in `_drafting_table`; it overlaps the
     parametrized leaf net (test 5) deliberately so the headline beta-test drift
     has its own self-documenting test.
  2. `test_chapters_manifest_is_documented` — assert a `[[chapters]]`
     table-array header appears in the extracted fence, then extract the
     `[[chapters]]` sub-block via `_chapters_block` (point 5) and assert **each**
     of the four `ChapterEntry`-derived field names (`number`, `slug`, `title`,
     `target_words`) appears as a `name =` line **within that sub-block**, not
     within the whole fence. The four names come from
     `dataclasses.fields(ChapterEntry)` (point 4), never from the emitted empty
     array. Running the four-field check against the sub-block (not the fence) is
     the B-R2.2 fix: it ensures the shared `slug`/`title` names are exercised
     inside the manifest example rather than being satisfied by their `[novel]`
     occurrences.
  3. `test_every_emitted_table_header_is_documented` — parametrized over
     `emitted_table_headers` (every distinct `[header]`/`[[header]]` line the
     serialised dump emits); each must appear as a `[header]`/`[[header]]`
     line in the fence. Row ids are the dotted headers `novel`, `phase`,
     `drafting`, `drafting.critic`, `drafting.fangirl`, `gates.knitting`,
     `gates.final`, `word_counts`. There is **no** `[gates]` row (parent-only
     table, no bare header emitted — D5) and **no** `[chapters]` row (the empty
     array emits a `chapters = []` leaf, not a header — D6; the manifest is
     checked by test 2).
     A new table added to the emitter without being documented fails here.
  4. `test_top_level_schema_scalar_is_documented` — a single non-parametrized
     assertion that the top-level scalar `schema_version` appears as a `name =`
     line (it has no table header, so it rides with the leaf net but is pinned
     by name for clarity). Optional; fold into test 5 if preferred.
  5. `test_every_emitted_leaf_is_documented` — parametrized over
     `emitted_leaf_names` (**every** emitted leaf at every depth, the B1 net,
     with the single name `chapters` excluded per D6 because it is documented as
     the `[[chapters]]` block, not a `chapters =` scalar — so there is **no**
     `…[chapters]` row); each must appear as a `name =` line in the fence. Row
     ids are the leaf names (`schema_version`, `convergence_target`, `done_30`,
     `final_pass_complete`, `by_chapter`, `completed`, …). This is the
     comprehensive drift net: a new leaf under **any** table — `[gates.final]`,
     `[word_counts]`, `[drafting.fangirl]`, … — added to the emitter without
     being documented fails here, closing the B1 gap that a two-scope guard left
     open.

- Each assertion carries a failure message citing design §5.1 and naming the
  drifted key or header, so a failure tells the author exactly which key to
  document.

Validation for item 2 (the red/green demonstration):

1. Before relying on the guard, prove it bites — **and prove the parametrized
   net bites**, not just the scalar tests (review round 1 B3). Temporarily
   revert the item-1 edit (or stash it) and run
   `pytest tests/test_state_layout_schema_guard.py -v`. Reverting item 1 removes
   both the `convergence_target` line and the `[[chapters]]` manifest block from
   the fence, so on a reverted reference exactly the following **three** rows
   **must** be RED (a guard whose parametrized rows all stay green on a reverted
   reference does not bite and must not ship):

   - `test_convergence_target_is_documented` (scalar pin — no
     `convergence_target =` line present).
   - `test_chapters_manifest_is_documented` (no `[[chapters]]` header present).
   - `test_every_emitted_leaf_is_documented[convergence_target]` — the
     `convergence_target` leaf row of the parametrized leaf net.

   Every **other** parametrized row must stay GREEN on the reverted reference.
   In particular **every** `test_every_emitted_table_header_is_documented[…]` row
   (`…[novel]`, `…[phase]`, `…[drafting]`, `…[drafting.critic]`,
   `…[drafting.fangirl]`, `…[gates.knitting]`, `…[gates.final]`,
   `…[word_counts]`) stays GREEN, because reverting item 1 touches no table
   header and all eight emitted headers are documented in the shipped fence.
   There is no `…[gates]` row and no `…[chapters]` row at all (D5/D6), so neither
   appears in the RED or the GREEN list — if either id materialises, the header
   net was derived from a type walk instead of the serialised dump; stop and fix
   the derivation (review round 3 B-R3.1). Likewise every other leaf row
   (`…[schema_version]`, `…[done_30]`, `…[completed]`, `…[by_chapter]`, …) and
   the `…[chapters]` leaf row's **absence** (it is excluded by D6) must hold. If
   a row that should be green is red, or a row that should be red is green, or an
   unexpected id appears, the parametrization is mis-wired — stop and fix the
   helper before proceeding (this is the false-green trap B3 guards against).
   Restore the item-1 edit and re-run — expect **all pass**. Capture both
   transcripts in `Artifacts and notes`, including the three named RED row ids.
2. `make test` — expect the full suite green, including the existing
   `tests/test_state_layout_reference.py` (proving the documentation edit did
   not trip the write-recipe guard).
3. `make lint`, `make check-fmt`, `make typecheck`, `make audit` — expect pass
   (the guard is a small, fully typed, docstringed test module; `interrogate`
   requires 100% docstring coverage).
4. `make all` — the aggregate gate; expect pass.

Commit item 2 once `make all` passes.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-2-1-8`.

Work item 1:

```bash
git branch --show   # expect: roadmap-2-1-8
# edit skill/novel-ralph/references/state-layout.md (fence + prose)
make fmt
make markdownlint
make nixie
git add skill/novel-ralph/references/state-layout.md
git commit -F <commit-message-file>   # never -m; see commit-message skill
```

Expected `make markdownlint` tail:

```plaintext
markdownlint ... 0 errors
```

Work item 2:

```bash
# create tests/test_state_layout_schema_guard.py
# RED check: prove the guard bites against an undocumented reference
git stash push -- skill/novel-ralph/references/state-layout.md
pytest tests/test_state_layout_schema_guard.py -v   # expect failures
git stash pop
pytest tests/test_state_layout_schema_guard.py -v   # expect all pass
make all
git add tests/test_state_layout_schema_guard.py
git commit -F <commit-message-file>
```

Expected RED transcript on a reverted reference — exactly these three rows fail
(B3); all other parametrized rows pass:

```plaintext
FAILED tests/test_state_layout_schema_guard.py::TestEmittedSchemaIsDocumented::test_convergence_target_is_documented
FAILED tests/test_state_layout_schema_guard.py::TestEmittedSchemaIsDocumented::test_chapters_manifest_is_documented
FAILED tests/test_state_layout_schema_guard.py::TestEmittedSchemaIsDocumented::test_every_emitted_leaf_is_documented[convergence_target]
```

If any *other* parametrized row appears in this RED list (for example
`test_every_emitted_leaf_is_documented[done_30]`), or if a
`test_every_emitted_table_header_is_documented[gates]` or `…[chapters]` row
exists at all (it must not — `gates` is a parent-only table emitting no bare
header and `chapters` emits a leaf line, not a header; D5/D6), the documentation
or the dump-derived sets are wrong — stop and reconcile before committing.

Expected GREEN transcript (abbreviated):

```plaintext
tests/test_state_layout_schema_guard.py ......                          [100%]
```

## Validation and acceptance

Acceptance is behaviour a human can verify:

- Reading `skill/novel-ralph/references/state-layout.md`, the
  `## state.toml schema` fence shows a `[[chapters]]` entry (with `number`,
  `slug`, `title`,
  `target_words`) and a `convergence_target` line in `[drafting.critic]`, and
  the prose defines both, citing design §5.1.
- `pytest tests/test_state_layout_schema_guard.py -v` fails when the two fields
  are not documented (demonstrated by stashing the item-1 edit; the three
  specific RED rows named in work item 2 step 1 must fail and no others) and
  passes when they are. The guard is comprehensive: it asserts **every**
  emitted leaf name and table header (as the serialised dump renders them) is
  documented, so any future undocumented field under any table also fails it.
- `make all` passes (Python build, format check, lint, typecheck, test —
  `make all` is `build check-fmt lint typecheck test`; it does **not** run
  `audit`, `markdownlint`, or `nixie`, which are invoked as separate gates
  below; review round 2 advisory A-R2.2).
- `make audit` passes (no new dependency introduced).
- `make markdownlint` and `make nixie` pass on the edited reference.

Quality criteria (what "done" means):

- Tests: `make test` green; the new guard fails before the documentation edit
  and
  passes after; the existing `tests/test_state_layout_reference.py` still green.
- Lint/typecheck: `make lint`, `make check-fmt`, `make typecheck` pass;
  `interrogate` 100% docstring coverage on the new module.
- Markdown: `make markdownlint` and `make nixie` pass.
- Security: `make audit` passes (no new dependency introduced).

Quality method: run `make all`, then `make markdownlint` and `make nixie`
(sequentially, never in parallel, to benefit from build caching).

## Idempotence and recovery

- Both work items are pure additions (Markdown lines, a new test file).
  Re-running
  the edits is safe; re-running the gates is safe.
- The RED demonstration uses `git stash push -- <reference>` and
  `git stash pop`;
  if the pop conflicts, resolve by restoring the documented reference from the
  committed item-1 version
  (`git checkout -- skill/novel-ralph/references/state-layout.md` if item 1 is
  already committed).
- No destructive operation is involved; the working tree returns to a clean
  state
  after each commit.

## Artifacts and notes

RED demonstration (2026-06-25). The committed item-1 edit makes the reference
unmodified at HEAD, so the RED check exercised the guard's predicates against
the pre-item-1 reference (`git show HEAD~1:…/state-layout.md`) rather than a
`git stash` of a working-tree edit. On that reverted reference exactly the
three planned rows are RED:

```plaintext
convergence_target documented: False   # test_convergence_target_is_documented
chapters header documented:    False   # test_chapters_manifest_is_documented
RED leaf rows: ['convergence_target']  # …leaf_is_documented[convergence_target]
RED header rows: []                    # every header row stays GREEN
header ids: ['novel', 'phase', 'drafting', 'drafting.critic',
            'drafting.fangirl', 'gates.knitting', 'gates.final', 'word_counts']
gates in headers: False                # parent-only table, no bare header (D5)
chapters in leaf net: False            # excluded (D6)
chapters in header net: False          # empty array emits a leaf, not a header
```

No `[gates]` or `[chapters]` id materialised in either net, confirming the
serialised-dump derivation (D5/D6) rather than a type walk.

GREEN demonstration (2026-06-25). `pytest tests/test_state_layout_schema_guard.py
-v` on the documented (committed) reference reports `35 passed`, including the
inline-table inner leaves (`blocker`/`major`/`minor`/`taste`) and the eight
header rows.

`make all` tail: `1124 passed, 1 skipped, 80 warnings`; `make all` exit 0;
`make audit` exit 0 (only the expected unauditable local `novel-ralph-skill`
skip). `markdownlint-cli2` on the edited reference and `make nixie` both clean.

## Interfaces and dependencies

- Emitter (read-only dependency):
  `novel_ralph_skill.state.build_initial_document`
  — re-exported from `novel_ralph_skill/state/__init__.py`. The guard imports
  it to derive the expected key set. Signature, unchanged by this task:

```python
def build_initial_document(
    *, title: str, slug: str, target_word_count: int, created_at: str
) -> tomlkit.TOMLDocument: ...
```

- Fixture (read-only dependency): `read_repo_text` from `tests/conftest.py`, a
  `RepoTextReader` callable `(*parts: str) -> str` reading a repo-relative file
  as UTF-8. The `RepoTextReader` type is imported under `if TYPE_CHECKING:`.

- New test module: `tests/test_state_layout_schema_guard.py`, defining
  `class TestEmittedSchemaIsDocumented` with the tests named above (two scalar
  pins, two parametrized nets over `emitted_table_headers` and
  `emitted_leaf_names`, and the optional `schema_version` pin). If a support
  helper is extracted to keep the module under 400 lines, place it at
  `tests/_state_schema_keys.py` as pure functions over the serialised dump text
  and the reference text (mirroring how `tests/_state_layout_scanner.py`
  carries pure helpers for the sibling guard). The helper exposes the
  dump-derived sets (`emitted_leaf_names` with `chapters` excluded per D6,
  `emitted_table_headers`), the fence extractor, and the two fence-anchored
  presence predicates plus the `[[chapters]]` sub-block extractor.

- Schema dependency (read-only): `ChapterEntry`, re-exported from
  `novel_ralph_skill.state` (verified: `novel_ralph_skill/state/__init__.py`
  `__all__` lists both `"ChapterEntry"` and `"build_initial_document"`, so the
  guard imports both from the package root). The guard reads its four field
  names via `dataclasses.fields(ChapterEntry)` for the chapter manifest check,
  because `init` emits an empty `chapters` array (Decision Log D4).

- No runtime `novel_ralph_skill/` code changes. No new external dependency
  (`dataclasses` and `re` are standard library; `tomlkit` is already locked).

## Revision note

Initial draft (2026-06-25). Decomposes roadmap task 2.1.8 into two atomic
items: (1) document `chapters` and `convergence_target` in `state-layout.md`
per design §5.1, and (2) add an emitted-schema-drift guard derived from
`build_initial_document`. No cuprum API is on the critical path for this task —
it touches Markdown documentation and a pytest guard only, using `tomlkit`
(already locked) and the standard library; the `firecrawl`/external-library
research mandate is therefore not load-bearing here (Decision Log D1, D3, D4).

Round 2 revision (2026-06-25). Resolves the three round-1 review blocking
points:

- B1 (guard too narrow): the guard now asserts **every** emitted leaf name and
  **every** emitted table header is documented, not just top-level tables plus
  `[drafting.critic]` leaves. The flattener yields `emitted_leaf_names` and
  `emitted_table_headers` over the whole document; the parametrized
  `test_every_emitted_leaf_is_documented` is the comprehensive drift net.
  Updated in Purpose, Risks (first risk), Surprises (new full-leaf
  observation), Decision Log D4, work item 2's helper points 2/5 and tests 3/5,
  and the acceptance section. This is the full drift net the roadmap promises;
  it costs nothing extra over the two-scope version because every other emitted
  leaf is already documented (verified by cross-reading the emitter against the
  fence).
- B2 (chapter sub-fields cannot be emitter-derived): the plan now states the
  chapter manifest sub-fields are read from `dataclasses.fields(ChapterEntry)`,
  not the emitted (empty) `chapters` array. Decision Log D4 is amended to the
  split "top-level and per-table leaf keys from the emitter; chapter sub-fields
  from `ChapterEntry`", removing the test-spec-vs-decision-log contradiction.
  Updated in Risks (new empty-array risk), Context (`ChapterEntry` bullet),
  Decision Log D4, work item 2 helper point 4 and test 2, and Interfaces.
- B3 (under-specified RED for parametrized rows): work item 2 step 1 and the
  Concrete-steps RED transcript now name the exact four rows that must go red
  on a reverted reference — `test_convergence_target_is_documented`,
  `test_chapters_manifest_is_documented`,
  `test_every_emitted_table_header_is_documented[chapters]`, and
  `test_every_emitted_leaf_is_documented[convergence_target]` — and require all
  other parametrized rows to stay green, so a mis-wired (non-biting)
  parametrization cannot ship green.

These revisions affect only the guard's test design and the plan's prose; the
two-item decomposition, the documentation edit, the validation commands
(`make all`, then `make markdownlint` and `make nixie`), and the
no-runtime-code constraint are unchanged.

Round 3 revision (2026-06-25). Resolves the two round-2 review blocking points
and folds in the three advisories:

- B-R2.1 (flattener unimplementable as written): the round-2 leaf net wrongly
  admitted the top-level `chapters` array as a leaf, because `chapters` and
  `phase.completed` are both empty `tomlkit.items.Array` and the plan gave no
  rule to tell them apart. The flattener now branches on the **position** of the
  key, not the `Array` type: the single top-level key `"chapters"` is the sole
  table-array header (in `emitted_table_headers`, excluded from
  `emitted_leaf_names`), while every other `Array` — concretely the empty
  `phase.completed` — is a leaf yielding its own name. New Decision Log D5, a
  new dedicated Risk, the empirical Surprises observation (both arrays length 0;
  `isinstance(v, Table)` misses `chapters`), and the rewritten work item 2
  helper point 2 all state this. Without it `…[chapters]` stayed RED green-after
  and the guard could never ship.
- B-R2.2 (`test_chapters_manifest_is_documented` false negative): the manifest
  field check ran against the whole fence, so `slug`/`title` (already under
  `[novel]`) passed even if omitted from the `[[chapters]]` example. A new
  `_chapters_block` helper extracts the `[[chapters]]` sub-block (header line to
  the next table header or fence end), and the four-field presence check now
  runs against that sub-block. Stated in a new Risk, work item 2 helper point 5
  (now three helpers), and test 2.
- A-R2.1 (table-blind name net): the leaf net's name-only, table-blind nature
  is now stated honestly as an accepted limitation (a new Risk and a Limitation
  note in helper point 2); per-occurrence coverage is restored where it matters
  by the B-R2.2 sub-block extraction.
- A-R2.2 (`make all` parenthetical): the acceptance bullet no longer claims
  `make all` runs `audit`; it now spells out `make all` =
  `build check-fmt lint typecheck test` and lists `make audit`,
  `make markdownlint`, and `make nixie` as separate gates.
- A-R2.3 (MD013 on fence comments): work item 1 step 2 now warns that
  fenced-code lines obey MD013 `code_block_line_length: 120` and the
  `[[chapters]]` manifest comment must stay well inside 120 columns.

The two-item decomposition, the no-runtime-code constraint, and the validation
commands were unchanged by round 3. (The B3 demonstration's RED rows were
further corrected in round 4 below — see that note.)

Round 4 revision (2026-06-25). Resolves the round-3 review blocking point
B-R3.1 (empirically reproduced):

- B-R3.1 (`gates` header row RED-green-after; `chapters` shape mis-modelled).
  The round-3 plan derived the header set from an `isinstance(v, Table)` walk of
  the in-memory document, which yields `gates` as a required header — but `gates`
  is a parent-only table carrying only the sub-tables `knitting` and `final` and
  **no scalar leaf**, so `tomlkit.dumps` emits **no bare `[gates]` line**, only
  `[gates.knitting]`/`[gates.final]` (verified in the worktree; design line 604
  fixes that form, never `[gates]`). So
  `test_every_emitted_table_header_is_documented[gates]` would have stayed
  RED-green-after, exactly the serialisation-shape hazard B-R2.1 fixed for
  `chapters` but left for `gates`. Verifying the dump also exposed that the
  round-3 premise "`chapters` emits a `[[chapters]]` header" was wrong: the empty
  array serialises as the bare leaf line `chapters = []`, not a header. The plan
  now adopts the PREFERRED fix: derive **both** the header net and the leaf net
  from `tomlkit.dumps(build_initial_document(...))`. The header net is the set of
  emitted `[header]`/`[[header]]` lines, so `gates` — and any future parent-only
  table — is excluded automatically with no special-case; the round-3 positional
  special-case is removed entirely. The leaf net is the set of emitted `key =`
  lines (plus the inline-table inner keys of `last_finding_counts`), with the
  single name `chapters` excluded (new Decision Log D6) because the reference
  documents it as the `[[chapters]]` manifest block, not a `chapters =` scalar.
  The factually-wrong "every table header appears save `[[chapters]]`" Surprises
  claim and the D5 "`chapters` is the only exception" framing are corrected: the
  header net has the single automatic `gates` exclusion (and no `chapters`
  header at all), and the leaf net has the single named `chapters` exclusion. The
  B3 RED demonstration and the Concrete-steps RED transcript are corrected to
  the **three** achievable RED rows (`test_convergence_target_is_documented`,
  `test_chapters_manifest_is_documented`,
  `test_every_emitted_leaf_is_documented[convergence_target]`); the round-3
  `test_every_emitted_table_header_is_documented[chapters]` row is removed
  because that id never exists. Updated in Purpose, Risks (the type-walk risk
  replaces the round-3 positional-special-case risk; the first risk now cites
  the serialised dump), Surprises (corrected `gates` and `chapters` observations,
  both with round-4 worktree evidence), Decision Log (D5 corrected, D6 added),
  work item 2 helper point 2 and test 3, the B3 demonstration, the Concrete-steps
  transcript, and the acceptance bullets.

The two-item decomposition, the no-runtime-code constraint, the documentation
edit (work item 1, which documents the populated `[[chapters]]` manifest and the
`convergence_target` line), and the validation commands (`make all`, then
`make markdownlint` and `make nixie`) are unchanged.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
post-merge review and audit of step 2.1 (`review:2.1.8`, `audit:2.1.8`). Execute
each as a small addendum pass — no plan or design-review cycle: make the change,
run `make all` (plus `make markdownlint`/`make nixie` for Markdown),
`coderabbit review --agent`, commit, and tick the matching roadmap sub-task on
merge. The substantial, cross-cutting follow-up was re-routed off this task: the
table-aware `(table, name)`-keyed leaf net and generic inline-table walk for the
schema-drift guard (`review:2.1.8`, two near-identical proposals merged) went to
a new roadmap step 7.30 (deferred schema-drift-guard hardening), because it
hardens a documentation-drift tripwire rather than advancing the step-2.1
schema-validator hypothesis. The three below are the small, localised fixes tied
to this completed task.

- [x] 2.1.8.1 — Document `[pending_turn]` in `state-layout.md` to fully
  reconcile the reference with design §5.1 (from review:2.1.8, low). Design §5.1
  names three fields added beyond the reference structure (`[chapters]`,
  `convergence_target`, and `[pending_turn]`); this task documented the first
  two because `init` emits them, leaving the transient mid-mutation
  `[pending_turn]` intent record (§3.4) undocumented in the authoritative
  on-disk reference. Add a `[pending_turn]` schema entry and a short prose
  subsection so the reference mirrors the transient on-disk shape, not only the
  `init` shape; note that the emitted-drift guard structurally cannot cover it
  because `init` never emits `[pending_turn]`. Docs-only; cite design §5.1 and
  §3.4. Gate with `make markdownlint` and `make nixie`.

- [x] 2.1.8.2 — Reconcile the initial `[drafting.critic].pass` seed with its
  documented "no pass run yet" semantics and pin the initial critic sub-state
  (from audit:2.1.8, Findings 1 and 2, both low). `novel_ralph_skill/state/
  initial.py` `_drafting_table` emits `critic["pass"] = 1`, but the reference
  documents `pass = 0` as "no pass run yet" — a schema-vs-reference value
  inconsistency of exactly the class this task set out to close, missed because
  the new guard checks key presence, not field values, and the initial critic
  sub-state (`pass`, `consecutive_clean`, `convergence_target`) is pinned by no
  test. Decide the intended value across `initial.py`, the corpus builder
  (`tests/working_corpus/_builder.py`), and the reference; the audit's
  lower-risk option (b) keeps `pass = 1` (the first pass is numbered 1 and is
  pending, not run) and corrects the reference comment and prose, recording the
  rationale beside the emitter. Then add a focused assertion to
  `test_initial_document_parses_then_carries_initial_fields` (or a sibling)
  pinning `pass`, `consecutive_clean`, and `convergence_target` to their
  intended values. Small value-only slice. Gate with `make all` (plus
  `make markdownlint`/`make nixie` for the reference edit).

- [x] 2.1.8.3 — Document the state-layout schema-drift guard in the developers'
  guide alongside the direct-edit guard (from audit:2.1.8, Finding 3, low). The
  guide carries a dedicated "The state-layout direct-edit guard" subsection for
  the sibling write-recipe guard but none for this task's schema-drift guard
  (`tests/test_state_layout_schema_guard.py`), the only tripwire preventing the
  `## state.toml schema` fence drifting from what `init` emits. Add a short "The
  state-layout schema-drift guard" subsection stating that the guard derives the
  required leaf and header nets from the serialised `build_initial_document(...)`
  dump, that adding an emitted field obliges a matching line in the fence, and
  that the two documented exclusions (`gates` parent-only header, `chapters`
  empty-array leaf) are deliberate; cross-reference design §5.1 and roadmap
  2.1.8. Docs-only. Gate with `make markdownlint` and `make nixie`.
