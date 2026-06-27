# Collapse the duplicated tomlkit inline-table builders onto one shared helper

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DRAFT (round 2)

## Purpose / big picture

Roadmap task 7.2.1 removes a five-way duplication of the same one-line
`tomlkit` idiom — "build a fresh inline table from a mapping" — so the
inline-table materialisation rule lives in genuinely one place. The roadmap's
`Success` line names *three* consumers (`recount`, `state/initial.py`, the
corpus builder), but step-7.2's Definition of Done is stricter than that list:
it demands "exactly one canonical implementation survives under one name … and
a test pins it so it cannot silently re-fork" (roadmap §7.2 preamble). Round-1
design review (`docs/execplans/roadmap-7-2-1.logisphere-review-r1.md`,
BLOCKING-1) established that two further byte-identical copies of the idiom
live in `novel_ralph_skill/commands/_set_chapters.py`, so honouring the
roadmap's three named copies while leaving those two in place would *not*
satisfy the step's DoD. This plan therefore takes the reviewer's preferred
**Option A**: route **all five** copies through one helper, so the DoD's
"exactly one canonical implementation" is literally true at the end.

`grep -rn 'tomlkit.inline_table(' novel_ralph_skill tests` returns exactly five
sites today (verified — see Decision Log D-INVENTORY):

1. `_inline_by_chapter` in `novel_ralph_skill/commands/_recount.py` (line 120;
   the `recount` mutator, which rebuilds `[word_counts].by_chapter` as a fresh
   inline table for a deterministic write);
2. `_inline` in `novel_ralph_skill/state/initial.py` (line 50; the `init`
   document builder, whose docstring already *admits* it is a hand-copied twin:
   "Mirrors `_inline` in the corpus builder …");
3. `_inline` in `tests/working_corpus/_builder.py` (line 37; the
   working-corpus reference materialiser);
4. `_zero_word_counts` in `novel_ralph_skill/commands/_set_chapters.py` (line
   183; seeds `[word_counts].by_chapter` with a zero count per freshly-planned
   chapter — passes a `dict[str, int]`); and
5. `_chapter_array` in `novel_ralph_skill/commands/_set_chapters.py` (line 161;
   builds the per-entry inline tables of the `[[chapters]]` array — passes a
   mixed `dict[str, int | str]`).

All five are the identical two statements: create `tomlkit.inline_table()`,
`table.update(...)` the mapping into it, return it. (Copy 1
(`_inline_by_chapter`) wraps the incoming mapping in `dict(...)`; copy 5
(`_chapter_array`) passes a four-key `dict` literal; copy 4
(`_zero_word_counts`) passes a `dict` comprehension; copies 2 and 3 (the two
`_inline` twins) pass the incoming mapping straight through. The shared helper
subsumes every form — see Risk "subtle argument-type differences".) This mirrors
how roadmap task 2.3.1 centralised the *counting*
rule into one `state/wordcount.py:recount_words` consumed everywhere, and how
task 2.2.1 centralised the *atomic write* into one
`state/document.py:write_text_atomically`. The inline-table builder is the same
single-home discipline applied to one more shared mechanism.

After this change a reader can observe success three ways. First, exactly one
function — `build_inline_table` in `novel_ralph_skill/state/document.py`,
re-exported from `novel_ralph_skill/state/__init__.py` — owns the
`tomlkit.inline_table()` + `update` idiom, and the five former copies are thin
call sites (visible by reading the now-shortened modules); the scoped
acceptance command in `## Validation and acceptance` makes "the five
definitions are gone and `build_inline_table` is the sole one" mechanically
checkable. Second, the `init`, `recount`, `set-chapters`, and corpus-tree
outputs are byte-for-byte unchanged on every input: every existing snapshot
(`tests/__snapshots__/test_novel_state_mutator_snapshots.ambr`) and every
round-trip property test
(`tests/test_state_document.py::test_noop_round_trip_over_corpus_trees`) stays
green without regeneration. Third, a new unit test pins the shared helper's
contract directly — it returns a `tomlkit.items.InlineTable`, serialises in the
mapping's insertion order, accepts mixed-type values, and does not alias the
caller's mapping — and the `initial.py` docstring no longer flags a hand-copied
twin.

This is a pure refactor. No new command, flag, library, dependency, schema
field, or envelope key is introduced, and no observable output changes for any
input the five paths produce today.

A *near*-duplication this plan deliberately does **not** fix is flagged for a
follow-up: `_chapter_array` in `_set_chapters.py` and `_chapters_array` in the
corpus builder both wrap `tomlkit.array()` + `multiline(True)` + a loop of
`build_inline_table(...)` appends. After this task both will call the shared
inline-table helper, but the *array-of-inline-tables* skeleton remains a
two-site near-copy. This is a distinct, wider idiom (an array builder, not an
inline-table builder) outwith roadmap 7.2.1's named scope; it is recorded in
Decision Log D-ARRAY-FOLLOWUP as a candidate 7.2.x addendum, not actioned here.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- `state.toml` round-trips losslessly through `tomlkit`; the single sanctioned
  writer remains `state/document.py:write_document_atomically` and no module
  serialises TOML by any other route (ADR-002; design §5.3). The shared helper
  builds *structure only* (an `InlineTable`); it never serialises or writes.
- The locked `tomlkit` version is `0.15.0` (`uv.lock` line 770). The helper
  relies only on `tomlkit.inline_table()`, `tomlkit.items.InlineTable`, and the
  insertion-order-preserving `update` inherited from `tomlkit`'s container; no
  new `tomlkit` API surface is introduced. (Verified — see Decision Log
  D-TOMLKIT.)
- This task touches **no** cuprum API. `cuprum` is the harness's subprocess
  catalogue/runner; inline-table construction is pure in-process `tomlkit`
  structure-building inside the `state` package, invoked by command bodies that
  never shell out for this work. No catalogue, allowlist, executable-path, or
  run/output option is in scope. (Stated explicitly per the standing
  external-library-pinning rule; there is no cuprum claim to pin because the
  plan leans on none.)
- `recount`'s deterministic-write contract is preserved exactly: rebuilding
  `[word_counts].by_chapter` as a fresh inline table in the mapping's
  (ascending) key order keeps a second `recount` over unchanged drafts
  byte-for-byte identical (`_recount.py` docstring; design §5.2 invariant 3;
  Decision Log D-KEY/D-CURRENT in `docs/execplans/roadmap-2-3-1.md`). The
  shared helper must preserve the caller's mapping order verbatim.
- `init`'s document remains schema-coherent: `[word_counts].by_chapter` stays a
  present empty inline table and `[drafting.critic].last_finding_counts` stays
  a populated inline table, so `parse_state` reads the fresh tree without loss
  (design §5.1, §5.2; `initial.py` module docstring).
- `set-chapters`'s document remains schema-coherent and byte-stable: the
  `[[chapters]]` array entries stay inline tables in the on-disk schema order
  (`number`, `slug`, `title`, `target_words`) and the seeded
  `[word_counts].by_chapter` stays a zero-per-chapter inline table, so the §5.4
  `word-counts-cover-drafts` coverage holds and `check` exits 0 immediately
  after `set-chapters` (`_set_chapters.py` docstrings; Decision D13 there).
- The working-corpus builder's *oracle independence* is not weakened. The corpus
  suite's independence lives in the schema/value *derivation* (`_specs.py`
  `derive_*` functions) and the cross-check *oracles* (`_oracle*.py`,
  `_live_draft.py`), which must keep re-deriving values without importing
  production derivation logic. The `_inline` helper carries **no** schema or
  derivation logic — it is pure `tomlkit` plumbing — so routing it through the
  shared production helper does not couple the oracle to production. (See
  Decision Log D-CORPUS; this fork is decided, not left open.)
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, comments,
  docstrings, and commit messages (AGENTS.md).
- No code file exceeds 400 lines (AGENTS.md). `state/document.py` is 268 lines
  today; adding one small helper stays well under the cap. `_set_chapters.py`
  is 356 lines today; routing two sites through the helper *removes* lines (the
  two `tomlkit.inline_table()`/`update` pairs become single calls), so the cap
  is not threatened.

## Tolerances (exception triggers)

- Scope: if the change touches more than 9 files or more than ~180 net lines,
  stop and escalate. (Expected: 5 source files — `state/document.py`,
  `state/__init__.py`, `state/initial.py`, `commands/_recount.py`,
  `commands/_set_chapters.py` — plus `tests/working_corpus/_builder.py`, plus
  1-2 test files, plus the two docs. The reroutes *remove* lines; the net add
  is the helper, its tests, and the docs notes.)
- Interface: the shared helper's public signature is fixed by this plan
  (`build_inline_table(pairs: cabc.Mapping[str, object]) -> tomlkit.items.InlineTable`).
  If a consumer needs a different signature, stop and escalate.
- Behaviour: if any existing snapshot or round-trip test requires regeneration
  to pass, stop and escalate — that signals an observable-output change this
  refactor must not cause. (Specifically: the `init`, `recount`, and
  `set-chapters` envelope snapshots in
  `tests/__snapshots__/test_novel_state_mutator_snapshots.ambr`, and the
  corpus-tree round-trip property, must stay green with **no**
  `--snapshot-update`.)
- Dependencies: if any new external dependency is required, stop and escalate.
- Iterations: if `make all` still fails after 3 fix attempts on a work item,
  stop and escalate.
- Scope creep into the array builder: if rerouting tempts the implementer to
  also unify `_chapter_array`/`_chapters_array` (the array-of-inline-tables
  near-copy), stop — that is the deferred D-ARRAY-FOLLOWUP, outwith this task.

## Risks

    - Risk: the five former copies differ subtly in argument type. Copies 1
      (`_recount._inline_by_chapter`) and 5 (`_set_chapters._chapter_array`)
      wrap the argument in `dict(...)` before `update`; copies 2, 3, and 4 pass
      the mapping straight to `update`. Copy 5 also carries *mixed-type* values
      (`int` number/target plus `str` slug/title). A naive merge could change
      the recount copy, alias a caller's mapping, or mis-handle mixed values.
      Severity: medium
      Likelihood: medium
      Mitigation: the shared helper accepts `cabc.Mapping[str, object]` (widest
      read-only input covering int-only, str-keyed, and mixed-value callers) and
      builds the table without retaining a reference to the argument
      (`tomlkit`'s `update` copies values into the table). Work item 1's unit
      test pins no-aliasing (mutating the source mapping after the call does not
      change the returned table), insertion-order preservation, **and** a
      mixed-type case (`{"number": 1, "slug": "a", "title": "A",
      "target_words": 10}` dumps with values intact and in order). Work item 1
      lands the helper and its tests before any call site is rerouted.

    - Risk: rerouting the corpus builder through a production import weakens the
      corpus suite's independence as a verification oracle.
      Severity: medium
      Likelihood: low
      Mitigation: decided in Decision Log D-CORPUS — the helper carries no
      schema/derivation logic, so the import does not couple the oracle's
      *derivation* to production. Work item 5 adds a comment at the corpus call
      site recording why this import is safe, and the round-trip property test
      over corpus trees stays green by construction.

    - Risk: a `tomlkit` behaviour difference between the system version
      (`0.14.0`) used for ad-hoc verification and the locked `0.15.0` could
      invalidate an assumption.
      Severity: low
      Likelihood: low
      Mitigation: pinned in Decision Log D-TOMLKIT against the upstream
      changelog — the only 0.14.0→0.15.0 change is TOML-1.1.0 parser support,
      which does not touch `inline_table`/`InlineTable`/`update`/`dumps`. The new
      unit test re-pins the behaviour against the actually installed version in
      CI.

    - Risk: the `initial.py` module docstring (lines 11-19) describes mirroring
      the corpus builder "field for field"; editing the `_inline` mirror note
      without updating that paragraph leaves a stale cross-reference.
      Severity: low
      Likelihood: medium
      Mitigation: work item 2 updates both the `_inline` docstring and the
      module-docstring "Mirrors … hand-copied twin" language together.

    - Risk: blind import removal. After deleting `_inline_by_chapter`,
      `commands/_recount.py`'s `import tomlkit` / `import tomlkit.items` become
      unused (Ruff F401 forces removal). But after rerouting the two
      `_set_chapters.py` sites, that module *still* uses `tomlkit.array()` (line
      158) and the `tomlkit.items.Array`/`InlineTable` return annotations (lines
      150, 174) plus `from tomlkit import TOMLDocument` (line 55), so its
      `import tomlkit` / `import tomlkit.items` must **stay**. Removing them
      blindly would break `_set_chapters.py`.
      Severity: medium
      Likelihood: medium
      Mitigation: each reroute work item names exactly which imports survive and
      which go, instructing the implementer to confirm with `leta refs` /
      `grep -n tomlkit <file>` before touching any import line; `make all`'s
      Ruff F401 + `ty check` catch a wrong call either way.

## Progress

    - [x] Work item 1 (2026-06-27): added `build_inline_table` to
      `state/document.py`, exported it from `state/__init__.py`, and pinned it
      with `tests/test_build_inline_table.py` (returns `InlineTable`, insertion
      order, mixed-type, no-alias, empty, plus a hypothesis dump-order property).
      Deviation: the unit tests live in a **new** `tests/test_build_inline_table.py`
      rather than appended to `tests/test_state_document.py`, because appending
      pushed that file to 453 lines and breached the 400-line cap (AGENTS.md);
      the cap takes precedence over the plan's "extend" wording.
    - [x] Work item 2 (2026-06-27): routed `state/initial.py`'s two inline
      tables through `build_inline_table`, deleted its `_inline` twin, and
      reworded the module docstring so it no longer admits a hand-copied
      inline-table twin (only the schema field set is mirrored). Added
      `test_initial_document_keeps_inline_table_form` pinning both structures
      stay `InlineTable`. `make all` green; init snapshot unchanged; coderabbit
      0 findings.
    - [x] Work item 3 (2026-06-27): routed `commands/_recount.py` through
      `build_inline_table`, deleted `_inline_by_chapter`, and dropped the
      now-unused `import tomlkit` / `import tomlkit.items`. Discovered a **sixth**
      consumer — `commands/_reconcile.py` re-used `_recount._inline_by_chapter`
      via a cross-module import (two call sites) — so that module is now routed
      through the shared `build_inline_table` too and its docstring updated (see
      Surprises / D-RECONCILE). The existing idempotence coverage
      (`test_recount_corrects_wrong_counts_and_is_idempotent`; the BDD step "a
      second recount leaves state.toml byte-for-byte unchanged") already pins the
      deterministic-write contract, so no new test was added. `make all` green;
      recount and reconcile snapshots unchanged; coderabbit 0 findings.
    - [x] Work item 4 (2026-06-27): routed both `commands/_set_chapters.py`
      sites (`_chapter_array`'s per-entry build and `_zero_word_counts`) through
      `build_inline_table`; kept `import tomlkit` / `import tomlkit.items` (still
      used by `tomlkit.array()` and the `Array`/`InlineTable` annotations) and
      `from tomlkit import TOMLDocument`. Added
      `test_set_chapters_writes_inline_table_form` asserting `by_chapter` and
      every `[[chapters]]` entry stay `InlineTable`. `make all` green;
      set-chapters snapshots unchanged; coderabbit 0 findings.
    - [x] Work item 5 (2026-06-27): routed `tests/working_corpus/_builder.py`'s
      three `_inline` call sites through `build_inline_table`, deleted `_inline`,
      and added the D-CORPUS safety comment at the (first) production import.
      Kept `import tomlkit` (still used by `tomlkit.table()`/`tomlkit.array()`).
      Deviation: did **not** add the optional inline-table-form assertion to
      `tests/test_working_corpus.py` — that file is already 534 lines and its
      state read goes through `tomllib`, which collapses inline tables to plain
      dicts and so cannot see the inline-vs-block distinction. The existing
      corpus-tree round-trip property
      (`test_noop_round_trip_over_corpus_trees`) already pins byte-stability (a
      block table would serialise differently), which the plan explicitly allows
      as sufficient ("No new test is strictly required"). Acceptance greps now
      pass: zero `tomlkit.inline_table(` under `tests`, exactly one under
      `novel_ralph_skill` (the helper). `make all` green.
    - [x] Work item 6 (2026-06-27): added a §5.3 single-home sentence naming
      `state/document.py:build_inline_table` and its consumers (`init`,
      `recount`, `reconcile`, `set-chapters`, corpus builder), and a
      developers-guide note recording the helper, its home, its five consumers,
      the D-CORPUS oracle-independence rationale, and the deferred
      D-ARRAY-FOLLOWUP. `make markdownlint`, `make nixie`, and `make all` all
      green; coderabbit 0 findings.

## Surprises & discoveries

    - Observation: appending the `build_inline_table` tests to
      `tests/test_state_document.py` breached the 400-line cap (453 lines).
      Evidence: `pylint` C0302 `too-many-lines (453/400)` on work item 1's first
      `make all`.
      Impact: the helper's tests live in a dedicated
      `tests/test_build_inline_table.py` instead; the validation-method note in
      `## Validation and acceptance` was updated to point the `tests` greps at
      that file rather than `test_state_document.py`.

    - Observation: a **sixth** consumer of the idiom existed that the round-2
      five-copy inventory (D-INVENTORY) missed.
      Evidence: `commands/_reconcile.py` did not contain a `tomlkit.inline_table(`
      literal (so the inventory grep did not catch it) but imported
      `_recount._inline_by_chapter` and called it at two sites (lines 145, 207).
      Deleting `_inline_by_chapter` in work item 3 broke `_reconcile.py`'s import
      (caught by `ty check`).
      Impact: `_reconcile.py`'s two call sites are now routed through the shared
      `build_inline_table` (see Decision D-RECONCILE); this *strengthens* the
      single-home DoD rather than widening scope, because the idiom is now truly
      sole-sourced. The inventory grep `rg 'tomlkit.inline_table('` remains valid
      for *literal* sites; the symbol-anchored greps in `## Validation and
      acceptance` (check 2) catch indirect re-use because `_inline_by_chapter` no
      longer exists for any module to import.

    - Observation: `make fmt` mdformat-reflows every tracked markdown file in the
      tree, not just touched docs.
      Evidence: a single `make fmt` produced ~250 modified `docs/`/`skill/` files
      of pure reflow churn (matching the long history of "spurious make-fmt
      mdformat churn" parking stashes on prior branches).
      Impact: do **not** run `make fmt` wholesale. Use `ruff format <file>` for
      Python and `make markdownlint` / `make nixie` for markdown validation; the
      reflow churn from this work item is parked in a discard stash.

## Decision log

    - Decision (D-INVENTORY): the canonical inventory is **five** copies, not
      three, and Option A (route all five through one helper) is taken over
      Option B (route the roadmap's named three and defer the two
      `_set_chapters.py` copies).
      Rationale: `grep -rn 'tomlkit.inline_table(' novel_ralph_skill tests`
      returns five sites (`_recount.py:120`, `initial.py:50`, `_builder.py:37`,
      `_set_chapters.py:161`, `_set_chapters.py:183`), confirmed in the worktree
      on 2026-06-27. Step-7.2's DoD requires "exactly one canonical
      implementation survives"; deferring the two `_set_chapters.py` copies
      (Option B) would leave that DoD visibly unmet and force the acceptance
      grep to assert a uniqueness the task did not deliver. Both
      `_set_chapters.py` callers are covered by the helper's
      `Mapping[str, object]` parameter (`_zero_word_counts` passes
      `dict[str, int]`; `_chapter_array`'s entries pass a mixed
      `dict[str, int | str]`), so folding them in costs two thin reroutes and no
      new signature. This supersedes round-1's three-copy framing.
      Date/Author: 2026-06-27, planning agent (round 2).

    - Decision: the shared helper lives in `novel_ralph_skill/state/document.py`
      named `build_inline_table`, re-exported from
      `novel_ralph_skill/state/__init__.py`.
      Rationale: `document.py` is already the canonical `tomlkit`
      construction-and-round-trip home for the state slice — it owns
      `open_pending_turn`, which builds `tomlkit.table()`/`tomlkit.array()`
      structures the same way. It is the module every state mutator already
      imports for the write path, so a `tomlkit`-structure helper sits naturally
      beside `write_document_atomically`. With Option A the consumers span the
      `state`, `commands`, and `tests` packages, and `document.py` is already
      imported across all three — reinforcing it as the right home (round-1
      review OPEN-1; recorded here so a future reader does not relitigate).
      `state/initial.py` is a *create-only* module and would couple the corpus
      builder and `_set_chapters` to `init`-specific code; a fresh
      `state/_inline.py` would be a one-function module for a two-line helper,
      against the "group by feature" guidance (AGENTS.md). The `build_` verb
      matches the existing `build_initial_document` and `build_envelope` naming.
      Date/Author: 2026-06-27, planning agent.

    - Decision (D-CORPUS): the corpus builder (`tests/working_corpus/_builder.py`)
      *is* routed through the shared production helper, despite the suite's
      deliberate oracle-independence discipline.
      Rationale: the roadmap entry names the corpus builder as one of the
      mandated consumers. The independence the corpus suite preserves is in
      *deriving schema and values* (`_specs.py:derive_*`) and in the *cross-check
      oracles* (`_oracle*.py`, `_live_draft.py`), none of which this helper
      touches. `_inline` is pure `tomlkit` plumbing with zero schema/derivation
      logic, so importing it from production does not let a production
      derivation bug hide a corpus mislabel. A call-site comment records this.
      Date/Author: 2026-06-27, planning agent.

    - Decision (D-TOMLKIT): the helper pins to `tomlkit.inline_table()`,
      `tomlkit.items.InlineTable`, and the insertion-order-preserving `update`.
      Rationale: verified empirically on the installed `tomlkit 0.14.0` that
      `tomlkit.inline_table()` returns a `tomlkit.items.InlineTable`, that
      `.update({"c":3,"a":1,"b":2})` then `tomlkit.dumps` yields
      `x = {c = 3, a = 1, b = 2}` (insertion order preserved, not sorted), that
      mixed-type values survive (`.update({"number":1,"slug":"a"})` dumps
      `{number = 1, slug = "a"}`), and that `update` is inherited (not
      overridden on `InlineTable`); mutating the source mapping after the call
      did not change the dump (no aliasing). The locked version is `0.15.0`
      (`uv.lock` line 770); the upstream changelog records the only
      0.14.0→0.15.0 change as "Update parser to support TOML spec v1.1.0"
      (<https://github.com/python-poetry/tomlkit/blob/0.15.0/CHANGELOG.md>),
      which does not touch these APIs. Round-1 design review independently
      confirmed
      these empirical claims. The new unit test re-pins this against the
      installed version so a future bump that breaks order is caught.
      Date/Author: 2026-06-27, planning agent.

    - Decision (D-SIG): the helper signature is
      `build_inline_table(pairs: cabc.Mapping[str, object]) -> tomlkit.items.InlineTable`.
      Rationale: `cabc.Mapping` is the widest read-only input that covers all
      five call sites — `_recount` and `_set_chapters._zero_word_counts` pass
      `Mapping[str, int]`, `initial`/`_builder` pass `dict[str, object]`, and
      `_set_chapters._chapter_array` passes a mixed `dict[str, int | str]`;
      `Mapping[str, object]` accepts all. The helper does not retain the
      argument, so a `Mapping` (not `MutableMapping`) input is correct and
      signals read-only intent. The return type is annotated as the qualified
      `tomlkit.items.InlineTable` with a runtime `import tomlkit.items`, matching
      the house pattern already used in `initial.py`, `_builder.py`, and
      `_recount.py` (round-1 review IMPROVEMENT-2) rather than a bare
      `from tomlkit.items import InlineTable` style fork.
      Date/Author: 2026-06-27, planning agent.

    - Decision (D-RECONCILE): `commands/_reconcile.py` is routed through the
      shared `build_inline_table` helper, not left importing the (deleted)
      `_recount._inline_by_chapter`.
      Rationale: discovered during work item 3 that `_reconcile.py` re-used
      `_recount._inline_by_chapter` via a cross-module import at two call sites
      (its `_recount_edit` and `_pending_turn_edit` both rebuild
      `[word_counts].by_chapter`). Retiring `_inline_by_chapter` (work item 3's
      stated step) therefore had to either keep the function alive purely for
      `_reconcile` (defeating the single-home goal) or route `_reconcile` onto
      the shared helper. The latter is the only choice consistent with step
      7.2's DoD — "exactly one canonical implementation survives" — so
      `_reconcile`'s two sites now call `build_inline_table` through its existing
      `from novel_ralph_skill.state import (...)` group. This is in-scope: it
      removes the last indirect re-use of the retired copy, and `_reconcile`
      mirrors `recount`'s write by design (its docstring says so), so it must use
      the same builder. The behaviour is unchanged — the reconcile/torn-turn
      snapshots and round-trip suites stay green with no regeneration.
      Date/Author: 2026-06-27, implementing agent (work item 3).

    - Decision (D-ARRAY-FOLLOWUP): the array-of-inline-tables near-duplication
      (`_set_chapters._chapter_array` vs corpus `_chapters_array`) is flagged,
      not fixed, in this task.
      Rationale: it is a *different* idiom — an array builder (`tomlkit.array()`
      + `multiline(True)` + a loop) wrapping the inline-table helper — and is
      outwith roadmap 7.2.1, which names only the inline-table builder. Folding
      it in would widen scope beyond the roadmap entry. Recorded here so a future
      reader can raise it as a 7.2.x addendum; the Tolerances "scope creep into
      the array builder" trigger guards against accidental inclusion.
      Date/Author: 2026-06-27, planning agent (round 2).

## Outcomes & retrospective

All six work items landed as six atomic commits, each gated green by `make all`
and reviewed by `coderabbit review --agent`. The three-way observability in
Purpose is met:

1. **One owner.** `build_inline_table` in `novel_ralph_skill/state/document.py`
   is the sole definition of the `tomlkit.inline_table()` + `update` idiom,
   re-exported from `novel_ralph_skill.state`. The acceptance greps hold:
   `rg 'def build_inline_table\(' novel_ralph_skill` returns exactly one match;
   `rg 'tomlkit\.inline_table\(' novel_ralph_skill` returns exactly one match
   (inside the helper); `rg 'tomlkit\.inline_table\(' tests` returns no matches.
2. **No behaviour change.** Every existing snapshot
   (`init`, `recount`, `set-chapters`, reconcile/torn-turn) and the corpus-tree
   round-trip property stayed green with **no** `--snapshot-update`, across all
   six commits.
3. **Pinned contract.** `tests/test_build_inline_table.py` pins the helper's
   return type, insertion-order preservation, mixed-type values, no-aliasing,
   the empty case, and a hypothesis dump-order property; the `initial.py`
   docstring no longer admits a hand-copied twin.

Deviations from the drafted plan, all recorded inline above:

- The inventory was **six** copies, not five: `commands/_reconcile.py` re-used
  `_recount._inline_by_chapter` via a cross-module import (two sites). It is now
  routed through the shared helper too (Decision D-RECONCILE), which strengthens
  the single-home DoD. This is the one material correction to the plan's
  D-INVENTORY count.
- The helper's unit tests live in a new `tests/test_build_inline_table.py`
  rather than appended to `tests/test_state_document.py` (the append breached the
  400-line cap; AGENTS.md takes precedence over the plan's "extend" wording).
- No new corpus-builder inline-table-form assertion was added (work item 5): the
  corpus state read goes through `tomllib`, which cannot see the inline-vs-block
  distinction, and the round-trip property already pins byte-stability, which the
  plan allows as sufficient.

Process note: `make fmt` mdformat-reflows every tracked markdown file in the
tree (not just touched docs); it was avoided in favour of `ruff format <file>`
plus `make markdownlint`/`make nixie`, and its one-off reflow churn was parked in
a discard stash.

The deferred D-ARRAY-FOLLOWUP (the `_chapter_array`/`_chapters_array`
array-of-inline-tables near-copy) remains a candidate 7.2.x addendum, untouched
here per the Tolerances scope-creep trigger.

## Context and orientation

The harness's primary memory is `working/state.toml`. State mutators read it
into a style-preserving `tomlkit` document, edit values in place, and write it
back through `tomlkit` so hand-authored comments and layout survive (ADR-002;
design §5.3). Two of the schema's tables are *inline* tables (TOML's
`{ key = value, … }` one-line form): `[word_counts].by_chapter` and
`[drafting.critic].last_finding_counts`; the `[[chapters]]` manifest is an
array whose *entries* are inline tables too.

Five modules build such inline tables and currently each carry their own
two-line builder:

- `novel_ralph_skill/commands/_recount.py` — `_inline_by_chapter` (lines
  102-122). The `recount` command re-derives `[word_counts]` from the chapter
  drafts and rebuilds `by_chapter` as a *fresh* inline table so a repeat
  recount over unchanged drafts is byte-for-byte stable. It takes a
  `cabc.Mapping[str, int]` and copies via `table.update(dict(by_chapter))`.
- `novel_ralph_skill/state/initial.py` — `_inline` (lines 43-52). The `init`
  document builder uses it for the empty `by_chapter` (line 137) and the
  populated `last_finding_counts` (line 100). Its docstring already says it
  "Mirrors `_inline` in the corpus builder", and the module docstring (lines
  11-19) says the whole module mirrors the corpus builder "field for field but
  … re-derived from `state/parse.py` rather than importing test code".
- `tests/working_corpus/_builder.py` — `_inline` (lines 35-39). The
  working-corpus reference builder materialises a `WorkingTreeSpec` as an
  on-disk `working/` tree, using `_inline` for `last_finding_counts` (line 70)
  and `by_chapter` (line 103) and the chapter-array entries (line 124).
- `novel_ralph_skill/commands/_set_chapters.py` — `_zero_word_counts` (lines
  172-185) and `_chapter_array` (lines 150-169). The `set-chapters` mutator
  populates `[chapters]` from the agent's plan. `_zero_word_counts` builds the
  `by_chapter` inline table seeded with a `0` per chapter (passes a
  `dict[str, int]`). `_chapter_array` builds the multiline `[[chapters]]` array
  whose entries are inline tables of `{number, slug, title, target_words}`
  (passes a mixed `dict[str, int | str]`). Both use the identical
  `tomlkit.inline_table()` + `update` idiom inline.

The single-home target is `novel_ralph_skill/state/document.py`, the lossless
`tomlkit` round-trip writer (268 lines). It already constructs `tomlkit`
structures in `open_pending_turn` and is the module every mutator imports for
the write path. The state package's public surface is
`novel_ralph_skill/state/__init__.py`, whose `__all__` re-exports `document.py`
symbols including `open_pending_turn`, `write_document_atomically`,
`load_document`, and `clear_pending_turn`, and `initial.py`'s
`build_initial_document`.

Import-graph facts (verified, round-1 review and `leta`/grep this round):
`document.py` imports nothing from `initial`, `commands`, or `tests`;
`parse.py` does not import `document`; `_set_chapters.py` and `_recount.py`
already import from `novel_ralph_skill.state`; `_builder.py` imports only
`tomlkit` and sibling `_specs` today. So every reroute's import is acyclic.

Terms used:

- *Inline table*: TOML's one-line `{ a = 1, b = 2 }` table form, distinct from a
  `[header]` block table. `tomlkit.inline_table()` builds an empty one.
- *Round-trip property*: a no-op load-then-write of a `state.toml` is
  byte-for-byte identical (ADR-002 Functional req 1), tested over a
  hand-authored fixture and over every corpus tree in
  `tests/test_state_document.py`.
- *Oracle independence*: the working-corpus suite deliberately re-derives
  expected schema and values without importing production *derivation* code, so
  a production bug cannot hide itself in the expectation. See
  `tests/working_corpus/_live_draft.py` module docstring.

## Plan of work

The work proceeds as six atomic, independently committable and gate-passable
work items. Work item 1 lands the shared helper and its test first (so the five
reroutes each have a verified target); items 2-5 reroute one module's call
sites each (item 4 covers both `_set_chapters.py` sites in one commit since
they share imports and a file); item 6 is the documentation single-home note
and markdown gates. Each item ends with `make all` green (and items touching
markdown additionally run `make markdownlint` and `make nixie`).

Read before starting any item: this ExecPlan in full; `AGENTS.md` (testing
rules, en-GB spelling, 400-line cap, abstraction/helper sweep policy);
`docs/adr-002-toml-round-trip-tomlkit.md`; design §5.3. Load the
`python-router` skill and follow it to the smaller skills it routes to:
`python-types-and-apis` (the `Mapping` signature and `InlineTable` return type),
`python-data-shapes` (read-only `Mapping` vs `dict` at the boundary), and
`python-testing` (fixture and parametrization shape). For the
no-aliasing/order/mixed-type invariants, load `python-verification` to confirm
whether a `hypothesis` property is warranted; see the per-item testing notes.

### Work item 1: add `build_inline_table` to `state/document.py` and pin it

Implements: ADR-002 (single `tomlkit` mechanism home); design §5.3 (round-trip
ownership); roadmap 7.2.1 ("one … helper lives in the state package") and the
§7.2 DoD ("exactly one canonical implementation survives … a test pins it");
AGENTS.md "Use functions and composition / Abstraction policy".

Docs to read: ADR-002; design §5.3; `state/document.py` (the
`open_pending_turn` construction precedent). Skills to load: `python-router` →
`python-types-and-apis` (return-type and `Mapping` parameter),
`python-data-shapes` (`Mapping` boundary), `python-testing`;
`python-verification` for the property-test go/no-go.

Add to `novel_ralph_skill/state/document.py`, beside `open_pending_turn`, a
function
`build_inline_table(pairs: cabc.Mapping[str, object]) -> tomlkit.items.InlineTable`.
Its docstring records that this is the single home of the inline-table
materialisation idiom the state slice re-derives `[word_counts].by_chapter`,
`[drafting.critic].last_finding_counts`, and the `[[chapters]]` entries from
(design §5.3; ADR-002); that it builds an empty inline table and `update`s
`pairs` into it **in the mapping's iteration order**, so a caller that hands an
order-stable mapping gets an order-stable table (the property `recount` relies
on for a byte-for-byte deterministic write — `recount` docstring; design §5.2
invariant 3); and that the returned table does not alias `pairs` because
`tomlkit` copies the values in, so a later mutation of `pairs` does not change
the table.

Import notes: annotate the return type as the qualified
`tomlkit.items.InlineTable`, matching the house pattern (round-1 review
IMPROVEMENT-2; D-SIG). `state/document.py` already imports `tomlkit`; add a
runtime `import tomlkit.items` only if not already present (confirm with
`grep -n 'import tomlkit' novel_ralph_skill/state/document.py`). `cabc` is
already aliased in the module's `TYPE_CHECKING` block; keep the parameter
annotation under `from __future__ import annotations` so no runtime import of
`collections.abc` is needed. Verify with the `leta` tool that no existing
`build_inline_table` symbol exists before adding (AGENTS.md abstraction-sweep
policy).

Export it: add `"build_inline_table"` to `__all__` in
`novel_ralph_skill/state/__init__.py` (alphabetical position, after
`"build_initial_document"`) and to the
`from novel_ralph_skill.state.document import (...)` group.

Tests to add (in the top-level `tests/` tree per AGENTS.md, never in the
package dir): extend `tests/test_state_document.py` with a focused unit test
class for `build_inline_table`, asserting:

1. the return value `isinstance(result, tomlkit.items.InlineTable)`;
2. insertion-order preservation — building from `{"b": 2, "a": 1}` and embedding
   it in a document `tomlkit.dumps`es to `… {b = 2, a = 1} …` (key order `b`
   then `a`, not sorted) — the load-bearing claim for `recount`'s determinism;
3. mixed-type values — building from
   `{"number": 1, "slug": "a", "title": "A", "target_words": 10}` dumps the
   four keys in order with `int` and `str` values intact (the `_chapter_array`
   case, the widest value-type call site);
4. no-aliasing — building from a `dict`, then mutating that `dict` after the
   call, leaves the returned table unchanged;
5. the empty case — `build_inline_table({})` serialises to an empty inline
   table `{}` (the `init` empty-`by_chapter` case).

These are example-based unit tests. Consider a `hypothesis` property for
order-preservation over arbitrary `dict[str, int]` (strategy: small dicts,
assert the dumped key order equals `list(source)`); load the `hypothesis` skill
only if `python-verification` confirms the property adds coverage the examples
do not (the order invariant over arbitrary insertion orders is a genuine
range-of-inputs invariant, so a property is justified here). Keep any property
test in the fast tier.

Validation: `make all` (runs `build check-fmt lint typecheck test`). Expect the
new test(s) to pass; expect `interrogate` 100% docstring coverage to stay green
(the new function is fully documented). The new test fails before the function
exists (import error) and passes after — note this red→green in the commit body.

### Work item 2: route `state/initial.py` through the shared helper

Implements: roadmap 7.2.1 ("the initial-document docstring no longer flags a
hand-copied twin"); design §5.1/§5.2 (init coherence); ADR-002.

Docs to read: `state/initial.py` module docstring (lines 1-24) and `_inline`
docstring (lines 43-52); design §5.1. Skills: `python-router` →
`python-data-shapes`, `python-testing`.

Edits in `novel_ralph_skill/state/initial.py`:

1. Import the shared helper:
   `from novel_ralph_skill.state.document import build_inline_table` (a sibling
   intra-package import; `document.py` does not import `initial.py`, so no
   cycle — confirm with `leta refs`).
2. Replace the two `_inline(...)` call sites (line 100 `last_finding_counts`,
   line 137 `by_chapter`) with `build_inline_table(...)`.
3. Delete the `_inline` function (lines 43-52).
4. Update the module docstring (lines 11-19): the "Mirrors … field for field …
   re-derived from `state/parse.py` rather than importing test code" paragraph
   must be reworded so it no longer implies a hand-copied inline-table twin —
   the inline-table idiom is now a shared import, while the *schema/value
   derivation* remains re-derived from `state/parse.py`. State explicitly that
   the inline-table builder is shared via `state/document.py` and only the
   schema shape is mirrored.

Note on imports: `initial.py` still uses `tomlkit.table()`/`tomlkit.array()`
elsewhere, so `import tomlkit` stays. The
`if typ.TYPE_CHECKING: import tomlkit.items as tomlitems` alias is still needed
for the other helpers' `tomlitems.Table` annotations — keep it.

Tests to add/update: the existing
`tests/test_state_initial.py::test_initial_document_parses_then_carries_initial_fields`
and `::test_initial_state_is_coherent` already pin that the built document
parses and is coherent — they must stay green unchanged (proving the reroute is
behaviour-preserving). Add one assertion (or a small focused test) that
`[word_counts].by_chapter` is an empty inline table and
`[drafting.critic].last_finding_counts` is a populated inline table in the
built document, pinning that the reroute kept the inline (not block) table
form. No snapshot regeneration is expected; if the init snapshot
(`tests/__snapshots__/test_novel_state_mutator_snapshots.ambr`
`test_init_success_envelope_snapshot`) changes, stop and escalate (a behaviour
change this refactor must not cause).

Validation: `make all`. Expect all `test_state_initial.py` and the init
snapshot test to stay green with no `--snapshot-update`.

### Work item 3: route `commands/_recount.py` through the shared helper

Implements: roadmap 7.2.1 (recount is a named consumer); design §5.2 invariant
3 and the deterministic-write contract (`_recount.py` docstring; ADR-002).

Docs to read: `_recount.py` `_inline_by_chapter` docstring (lines 102-122) and
the `recount` docstring (lines 193-225); `docs/execplans/roadmap-2-3-1.md`
Decision Log D-KEY/D-CURRENT (the determinism rationale). Skills:
`python-router` → `python-data-shapes` (the `Mapping[str, int]` →
`Mapping[str, object]` widening is safe), `python-testing`.

Edits in `novel_ralph_skill/commands/_recount.py`:

1. Add `build_inline_table` to the existing
   `from novel_ralph_skill.state import (...)` group (lines 38-42), keeping the
   group alphabetical.
2. Replace `_inline_by_chapter(by_chapter)` at line 234 with
   `build_inline_table(by_chapter)`.
3. Delete `_inline_by_chapter` (lines 102-122). **Then** remove the now-unused
   `import tomlkit` (line 22) and `import tomlkit.items` (line 23): after the
   reroute, the only remaining `tomlkit` mentions in `_recount.py` are inside
   the deleted function and a docstring word at line ~196 — confirm with
   `grep -n 'tomlkit' novel_ralph_skill/commands/_recount.py` that no live code
   reference survives before removing the imports. (Ruff F401 will flag them if
   left; `ty check`/import errors will flag them if removed wrongly.)

Note: the former `_inline_by_chapter` copied via `dict(by_chapter)`; the shared
helper does not need that copy because it does not retain the argument and
`recount` passes a freshly built `by_chapter` mapping. The determinism contract
is unchanged because the shared helper preserves the caller's (ascending) key
order — pinned by work item 1's order test.

Tests to add/update: the existing recount suites must stay green:
`tests/test_recount_unit.py`, `tests/test_recount_e2e.py`, and the recount
snapshot `tests/__snapshots__/test_novel_state_mutator_snapshots.ambr`
(`test_recount_success_envelope_snapshot`). The behavioural determinism — a
second `recount` over unchanged drafts yields a byte-for-byte identical
`state.toml` — is the load-bearing property; if an idempotent-recount test does
not already exist in `tests/test_recount_e2e.py` or the recount BDD steps
(`tests/steps/recount_steps.py`), add one: run `recount` twice over a corpus
tree with at least two non-empty chapters and assert the two `state.toml` byte
strings are identical. This pins that the helper reroute preserved the
deterministic-write contract end-to-end. No snapshot regeneration expected;
escalate if any recount snapshot churns.

Validation: `make all`. Expect recount unit/e2e/snapshot suites green.

### Work item 4: route both `commands/_set_chapters.py` sites through the shared helper

Implements: roadmap 7.2.1's intent and the §7.2 DoD ("exactly one canonical
implementation survives") — these two copies are the ones round-1 review
(BLOCKING-1) identified as blocking a true single home; design §5.1/§5.2 and
`_set_chapters.py`'s Decision D13 (the seeded zero counts and inline
`[[chapters]]` entries).

Docs to read: `_set_chapters.py` `_chapter_array` docstring (lines 150-157) and
`_zero_word_counts` docstring (lines 172-185); the `set_chapters` step list
(docstring lines 231-322). Skills: `python-router` → `python-data-shapes` (the
mixed-value `Mapping[str, object]` boundary for `_chapter_array`),
`python-testing`.

Edits in `novel_ralph_skill/commands/_set_chapters.py`:

1. Add `build_inline_table` to the existing
   `from novel_ralph_skill.state import (...)` group (lines 43-49), keeping the
   group alphabetical.
2. In `_chapter_array` (lines 158-168): replace the per-entry
   `table = tomlkit.inline_table(); table.update({...}); array.append(table)`
   block with `array.append(build_inline_table({...}))`, passing the same
   four-key `{number, slug, title, target_words}` mapping in the same order.
   The surrounding `tomlkit.array()` + `array.multiline(multiline=True)` stays.
3. In `_zero_word_counts` (lines 183-184): replace
   `table = tomlkit.inline_table(); table.update({...}); return table` with
   `return build_inline_table({f"{entry.number:02d}": 0 for entry in ordered})`.
4. **Keep** `import tomlkit` (line 30) and `import tomlkit.items` (line 31):
   `_chapter_array` still calls `tomlkit.array()` (line 158) and is annotated
   `-> tomlkit.items.Array` (line 150); `_zero_word_counts` is annotated
   `-> tomlkit.items.InlineTable` (line 174); and
   `from tomlkit import TOMLDocument` (line 55) is still used. Confirm with
   `grep -n 'tomlkit' novel_ralph_skill/commands/_set_chapters.py` that live
   references remain before deciding on any import line — do **not** mirror
   work item 3's import removal here.

Tests to add/update: the existing `set-chapters` suites must stay green:
`tests/test_set_chapters_unit.py`, `tests/test_set_chapters_e2e.py` (or the
equivalently named files — locate with `leta files` /
`grep -rl set_chapters tests`), and the `set-chapters` snapshot in
`tests/__snapshots__/test_novel_state_mutator_snapshots.ambr`
(`test_set_chapters_success_envelope_snapshot` or equivalent). The load-bearing
behaviours to keep green: (a) the written `[[chapters]]` entries are inline
tables in `number, slug, title, target_words` order; (b)
`[word_counts].by_chapter` is seeded with a zero per chapter as an inline
table; (c) `check` exits 0 immediately after `set-chapters` (the §5.4
coverage). If a unit assertion on the inline-table form of either structure
does not already exist, add one (assert
`isinstance(document["word_counts"]["by_chapter"], tomlkit.items.InlineTable)`
and that each `[[chapters]]` entry is an `InlineTable`). No snapshot
regeneration expected; escalate if any `set-chapters` snapshot churns.

Validation: `make all`. Expect every `set-chapters` unit/e2e/snapshot suite
green with no `--snapshot-update`.

### Work item 5: route `tests/working_corpus/_builder.py` through the shared helper

Implements: roadmap 7.2.1 (corpus builder is a named consumer); the corpus
oracle-independence discipline (`tests/working_corpus/_live_draft.py`
docstring; this plan's Decision Log D-CORPUS).

Docs to read: `_builder.py` module docstring (lines 1-10) and `_inline` (lines
35-39); `_live_draft.py` module docstring (oracle independence). Skills:
`python-router` → `python-testing`.

Edits in `tests/working_corpus/_builder.py`:

1. Import the production helper:
   `from novel_ralph_skill.state.document import build_inline_table`. This is
   the *first* production import in `_builder.py` (today it imports only
   `tomlkit` and sibling `_specs`), so add a one-line comment recording why it
   is safe: the helper carries no schema/derivation logic, so importing it does
   not couple the corpus suite's value-derivation oracle to production
   (D-CORPUS).
2. Replace the three `_inline(...)` call sites (line 70 `last_finding_counts`,
   line 103 `by_chapter`, line 124 chapter-array entries) with
   `build_inline_table(...)`.
3. Delete the `_inline` function (lines 35-39).
4. **Keep** `import tomlkit`: `_builder.py` still calls `tomlkit.table()`,
   `tomlkit.array()`, and annotates `tomlitems.*` return types elsewhere.
   Confirm with `grep -n 'tomlkit' tests/working_corpus/_builder.py`.

Tests to add/update: the corpus round-trip and coherence suites must stay green
unchanged — they *are* the test that the corpus trees still materialise
identically:
`tests/test_state_document.py::test_noop_round_trip_over_corpus_trees`,
`tests/test_working_corpus.py`, and any suite that materialises a corpus tree
(`tests/test_drafting_bijection_corpus.py`,
`tests/test_working_corpus_disk_divergence.py`). No new test is strictly
required — the existing corpus-tree round-trip property already pins that the
materialised bytes are unchanged — but add a one-line assertion in
`tests/test_working_corpus.py` (or wherever a built tree is parsed) that a
materialised tree's `[word_counts].by_chapter` is an inline table, so a future
regression from inline to block table form is caught directly rather than only
via the round-trip bytes.

Validation: `make all`. Expect every corpus-tree suite green with no snapshot
or fixture regeneration.

### Work item 6: documentation single-home note and markdown gates

Implements: AGENTS.md "Documentation maintenance" / "Abstraction … re-use
policy: record the decision in architecture, design, or developers-guide docs";
design §5.3 ownership; the §7.2 DoD ("it is documented as the single source of
truth").

Docs to read: design §5.3; `docs/developers-guide.md` (the existing single-home
notes — the `recount_words` counting-rule note at line ~1244, and the
`conftest.py` / cross-command single-home notes — to mirror their style);
AGENTS.md markdown guidance (80-col prose wrap, dashes for bullets). Skills:
`python-router` not needed here; this item is markdown only.

Edits:

1. In `docs/novel-ralph-harness-design.md` §5.3, add a single-home sentence
   recording that the inline-table materialisation idiom has one home
   (`state/document.py:build_inline_table`) consumed by `init`, `recount`,
   `set-chapters`, and the corpus builder. Phrase it in the style of the
   developers-guide `recount_words` note (round-1 review IMPROVEMENT-1: §5.3 as
   written is only about choosing `tomlkit` over an owned serialiser and has no
   pre-existing single-writer sentence to "mirror", so model the new sentence
   on the developers-guide note rather than claiming to mirror §5.3 prose).
   Keep it to the existing §5.3 prose density.
2. In `docs/developers-guide.md`, add a short note under the relevant
   single-source/DRY heading recording the helper, its home, its four consumers
   (`init`, `recount`, `set-chapters`, corpus builder), and the D-CORPUS
   rationale (why the corpus builder may import it without weakening oracle
   independence), so a future fifth consumer inherits the decision instead of
   re-forking. Optionally note D-ARRAY-FOLLOWUP (the array-of-inline-tables
   near-copy is a separate, deferred follow-up) so a future reader does not
   mistake it for an oversight.

Tests: none (documentation only). Validation: `make markdownlint` and
`make nixie` (no Mermaid changes expected, but `make nixie` is required for any
markdown touch per the standing rules), plus `make all` to confirm nothing else
regressed. Run `make fmt` first to normalise table/markdown formatting
(AGENTS.md).

## Concrete steps

Run all commands from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-2-1`.

Per work item:

1. Make the edits described above (use `leta show`/`leta refs` to navigate and
   confirm no import cycle or surviving `_inline`/`_inline_by_chapter`
   reference, and `grep -n 'tomlkit' <file>` before touching any import line).
2. Run the gate `make all`. Expect the tail to report the Ruff format check,
   `ruff check`, `interrogate` at 100%, Pylint, `ty check`, and `pytest` all
   passing. A representative green tail:

        ==== N passed in T.Ts ====

3. For work item 6 (markdown), additionally run `make markdownlint` and
   `make nixie`. Expect both to exit 0 with no findings.
4. Commit the work item with a file-based message (use the `commit-message`
   skill; never `-m`), en-GB imperative subject ≤ ~50 chars, body explaining
   what and why, noting the red→green for any new test.

After each commit, re-read this plan's `Progress` section and tick the
completed item with a timestamp.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes; the new `build_inline_table` unit test(s) fail
  before work item 1's function exists and pass after; every existing recount,
  init, set-chapters, corpus, and round-trip suite stays green with **no**
  snapshot or fixture regeneration.
- Lint/typecheck/format: `make check-fmt`, `make lint` (Ruff + 100%
  `interrogate` + Pylint), and `make typecheck` (`ty check`) all pass.
- Audit: `make audit` (`pip-audit`) passes (no new dependency added).
- Markdown (work item 6): `make markdownlint` and `make nixie` pass.
- Structure: exactly one inline-table builder exists in the tree — see the
  scoped command below. The five former copies are gone; `build_inline_table`
  is the sole definition site.

Quality method (how we check) — mechanically checkable, not eyeballed:

1. The five former definitions are gone. Each of these greps must return **no
   matches** (exit 1):

        rg -n 'def _inline_by_chapter' novel_ralph_skill/commands/_recount.py
        rg -n 'def _inline\b' novel_ralph_skill/state/initial.py
        rg -n 'def _inline\b' tests/working_corpus/_builder.py

   The two `_set_chapters.py` enclosing functions (`_zero_word_counts` and
   `_chapter_array`) *survive* but no longer call `inline_table`, so the "def
   gone" greps above do not cover them. Instead assert the idiom itself is gone
   from that file:

        rg -n 'tomlkit.inline_table\(' novel_ralph_skill/commands/_set_chapters.py

   must return **no matches** (exit 1).

2. `build_inline_table` is the **sole** owner of the idiom, anchored on the
   helper symbol rather than the raw `tomlkit.inline_table(` literal (which can
   also appear in comments or docs). First, the helper is defined exactly once:

        rg -n 'def build_inline_table\(' novel_ralph_skill

   must return **exactly one match**, in
   `novel_ralph_skill/state/document.py`. Second, the production tree's only
   `tomlkit.inline_table()` *call* is inside that helper body:

        rg -n 'tomlkit\.inline_table\(' novel_ralph_skill

   must return **exactly one match**, on the line inside `build_inline_table` in
   `novel_ralph_skill/state/document.py`. Third, every former consumer now
   reaches the idiom through the shared symbol:

        rg -n 'build_inline_table\(' novel_ralph_skill tests

   must list the five reroute call sites (`initial.py` ×2, `_recount.py`,
   `_set_chapters.py` ×2, `_builder.py` ×3) plus the helper definition and the
   helper's own tests in `tests/test_build_inline_table.py` — and **no**
   surviving `tomlkit.inline_table(` call under `tests` outwith that file:

        rg -n 'tomlkit\.inline_table\(' tests

   must return **no matches** (exit 1), since the corpus builder now routes
   through the shared helper and the helper's tests call `build_inline_table`
   rather than the raw `tomlkit` idiom.

3. `leta refs build_inline_table` lists the five call sites (`initial.py` ×2 in
   one function each, `_recount.py`, `_set_chapters.py` ×2, `_builder.py` ×3
   appends) plus the unit test, and the single definition in `document.py`.
   This confirms the call sites import the shared symbol; it is the *companion*
   to checks 1-2 (which prove the old definitions are gone), not a substitute
   for them.

Acceptance is observable: after the change, `init`, `recount`, `set-chapters`,
and every corpus tree produce byte-for-byte identical `state.toml` output
(every snapshot and the corpus-tree round-trip property green without
regeneration); the single helper owns the idiom (checks 1-3 above pass); and the
`initial.py` docstring no longer admits a hand-copied twin. Step-7.2's DoD —
"exactly one canonical implementation survives under one name, it is documented
as the single source of truth, and a test pins it so it cannot silently
re-fork" — is met by the single `build_inline_table`, the work-item-6 docs
notes, and the work-item-1 unit test respectively.

## Idempotence and recovery

Every work item is a pure structural refactor with no destructive disk
operation; re-running an item's edits is safe (the edits are idempotent string
replacements, and `make all` is re-runnable). If a reroute reddens a snapshot
or round-trip test, that is the escalation signal (Tolerances → Behaviour):
revert that work item's commit (`git revert`) and escalate rather than
regenerating the snapshot. Because items 2-5 are independent reroutes of
distinct files, a failure in one does not block committing the others; land
work item 1 first so each reroute has a verified target.

## Artifacts and notes

The single load-bearing snippet is the helper's signature and body shape (the
two statements every copy reduces to):

        def build_inline_table(
            pairs: cabc.Mapping[str, object],
        ) -> tomlkit.items.InlineTable:
            table = tomlkit.inline_table()
            table.update(pairs)
            return table

The two `_set_chapters.py` call-site reductions — `_chapter_array` appends a
`build_inline_table({...})` per entry (instead of `inline_table()` + `update` +
`append`), and `_zero_word_counts` returns
`build_inline_table({f"{entry.number:02d}": 0 for entry in ordered})` (instead
of `inline_table()` + `update` + `return`):

        array.append(build_inline_table({
            "number": entry.number,
            "slug": entry.slug,
            "title": entry.title,
            "target_words": entry.target_words,
        }))

        return build_inline_table(
            {f"{entry.number:02d}": 0 for entry in ordered}
        )

## Interfaces and dependencies

No new external dependency. The locked `tomlkit 0.15.0` (`uv.lock` line 770) is
the only library involved, used through its existing `inline_table`,
`items.InlineTable`, and `dumps` API. This task uses **no** cuprum API (see
Constraints).

In `novel_ralph_skill/state/document.py`, define:

        def build_inline_table(pairs: cabc.Mapping[str, object]) -> tomlkit.items.InlineTable:
            …

re-exported from `novel_ralph_skill/state/__init__.py` (`__all__` entry
`"build_inline_table"`). Consumed by:

- `novel_ralph_skill/state/initial.py` (via
  `from novel_ralph_skill.state.document import build_inline_table`),
- `novel_ralph_skill/commands/_recount.py` (via the existing
  `from novel_ralph_skill.state import (...)` group),
- `novel_ralph_skill/commands/_set_chapters.py` (via the existing
  `from novel_ralph_skill.state import (...)` group), and
- `tests/working_corpus/_builder.py` (via
  `from novel_ralph_skill.state.document import build_inline_table`).

## Revision note

Round 2 (2026-06-27): resolved the two blocking points from
`docs/execplans/roadmap-7-2-1.logisphere-review-r1.md`. (1) BLOCKING-1: adopted
the reviewer's preferred Option A — the canonical inventory is now five copies
(adding `_set_chapters.py`'s `_zero_word_counts` and `_chapter_array`), a new
work item 4 reroutes both, and the Purpose/Context/Tolerances/Decision-Log
(D-INVENTORY) text no longer claims a uniqueness the task did not deliver; the
true single home now satisfies step-7.2's DoD. (2) RISK-1: rewrote
`## Validation and acceptance` into three mechanically-checkable scoped
commands (per-file "def gone" greps, a "`tomlkit.inline_table(` gone from
`_set_chapters.py`" grep, and an "exactly one definition under
`novel_ralph_skill`" grep), with `leta refs` demoted to a companion check.
Folded in the reviewer's green notes: IMPROVEMENT-1 (model the §5.3 sentence on
the developers-guide `recount_words` note rather than a non-existent §5.3
"single-writer discipline"), IMPROVEMENT-2 / D-SIG (annotate the qualified
`tomlkit.items.InlineTable` with a runtime `import tomlkit.items`, matching the
house pattern, and drop the TYPE_CHECKING-vs-runtime waffle), and OPEN-1
(recorded in the home Decision why `document.py` remains correct under the
wider Option-A scope). Added Decision D-ARRAY-FOLLOWUP and a Tolerances trigger
to flag — but not fix — the `_chapter_array`/`_chapters_array` array-builder
near-duplication, and a "blind import removal" Risk capturing that
`_recount.py`'s `tomlkit` imports go while `_set_chapters.py`'s stay. Work-item
count rose from five to six; net-scope Tolerance widened from 8 files/150 lines
to 9 files/180 lines.
