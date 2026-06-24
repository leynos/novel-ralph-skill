# Post-merge audit — roadmap task 2.3.1

Audit of the codebase after roadmap task 2.3.1 ("Implement `recount` as a pure
aggregation over chapter drafts") merged to `main` at commit `b338562`. The
slice adds the `recount` mutator of `novel-state`, which re-derives
`[word_counts].current` and `[word_counts].by_chapter` from the on-disk chapter
drafts so a human never types a word count by hand (design §4.1). It is split
across three places: the pure aggregation helper
[`state/wordcount.py`](../../novel_ralph_skill/state/wordcount.py)
(`recount_words`), the mutator body
[`commands/_recount.py`](../../novel_ralph_skill/commands/_recount.py)
(`recount`), and the registration plus a new `_working_dir` helper in
[`commands/_state_mutators.py`](../../novel_ralph_skill/commands/_state_mutators.py)
and [`commands/novel_state.py`](../../novel_ralph_skill/commands/novel_state.py).

The slice is sound and very well covered. The pure helper is pinned against the
corpus oracle by a Hypothesis property and an example-based unit test
([`test_state_wordcount.py`](../../tests/test_state_wordcount.py)); the mutator
body has unit, refusal, idempotence, and property coverage
([`test_recount_unit.py`](../../tests/test_recount_unit.py)); the externally
observable behaviour is proven by a `pytest-bdd` scenario
([`test_recount_bdd.py`](../../tests/test_recount_bdd.py),
[`recount_steps.py`](../../tests/steps/recount_steps.py)) and an entry-point e2e
([`test_recount_e2e.py`](../../tests/test_recount_e2e.py)). The fault boundary
(absent `draft.md` → `0`; undecodable/unreadable draft → exit `3`) is pinned on
both sides, and the docstrings are unusually thorough.

None of the findings below is a blocking defect; all are low-severity hygiene
items. The dominant themes are (1) a small triplication of a `tomlkit`
inline-table helper now that `recount` adds a third copy, and (2) two stale doc
references that the 2.3.1 delivery left behind even though it documented the new
command well elsewhere.

Trail followed: explored with `leta` (`leta files`, `leta refs`, `leta show`)
over `commands/_recount.py`, `commands/_state_mutators.py`,
`commands/novel_state.py`, `state/wordcount.py`, `state/initial.py`, and
`state/__init__.py`; traced history with `sem diff --commit b338562` and
`git show b338562`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §3.2/§3.3/§3.4/§4.1/§5.2,
`docs/users-guide.md`, `docs/developers-guide.md` ("Checker/mutator
segregation", "State mutators"), prior `docs/issues/audit-2.2.2.md`, and
`AGENTS.md`. Loaded the `leta`, `sem`, and `python-router` skills. Each finding
records a category, location, description, concrete proposed fix, and severity.

## Finding 1 — `tomlkit` inline-table builder triplicated across the codebase

- Category: duplication
- Severity: low
- Location:
  [`commands/_recount.py`](../../novel_ralph_skill/commands/_recount.py) lines
  82–102 (`_inline_by_chapter`);
  [`state/initial.py`](../../novel_ralph_skill/state/initial.py) lines 43–52
  (`_inline`);
  [`tests/working_corpus/_builder.py`](../../tests/working_corpus/_builder.py)
  lines 35–38 (`_inline`).

The same two-line idiom — `table = tomlkit.inline_table(); table.update(...)`,
returning the populated `InlineTable` — now exists in three places. `recount`
added the third copy (`_inline_by_chapter`). The bodies are identical apart from
the parameter type (`Mapping[str, int]` versus `dict[str, object]`) and a
docstring; `initial.py`'s `_inline` even already builds the *initial* empty
`by_chapter` table, so production has two copies of "build the `by_chapter`
inline table" specifically. `initial.py`'s docstring states its `_inline`
"mirrors `_inline` in the corpus builder", which is an explicit acknowledgement
of the drift this finding flags.

Proposed fix: promote a single `inline_table_from(pairs: Mapping[str, object])`
helper into the `state` package (e.g. a small `state/_tomlkit.py` re-exported
from `state/__init__.py`, beside `write_document_atomically`), have
`_recount.py` and `initial.py` call it, and let the corpus builder import it too
(or keep the test copy but pin it equal). This keeps the one round-trip-style
rule — how an inline table is materialised so the schema parser reads it back —
in one place, consistent with `wordcount.py` having centralised the one counting
rule.

## Finding 2 — Developers' guide subsection heading omits `recount`

- Category: inconsistency
- Severity: low
- Location:
  [`docs/developers-guide.md`](../../docs/developers-guide.md) line 430, heading
  "### State mutators (`init`, `set-cursor`, `advance-phase`)".

The 2.3.1 commit expanded this subsection's body to fully document `recount`
(lines 493–511), and the prose throughout the section now enumerates
`init`/`set-cursor`/`advance-phase`/`recount` consistently. The *heading*,
however, still lists only the original three mutators, so the table of contents
and a skim-reader see a section that claims not to cover `recount` while its body
does. `sem diff --commit b338562` flagged this heading as modified only because
the content beneath it shifted; the heading text itself was never updated.

Proposed fix: update the heading to "### State mutators (`init`, `set-cursor`,
`advance-phase`, `recount`)" to match the section body and the parallel
enumerations elsewhere in the guide.

## Finding 3 — `novel_state.py` module docstring still calls `recount` a "later task"

- Category: docs-gap
- Severity: low
- Location:
  [`commands/novel_state.py`](../../novel_ralph_skill/commands/novel_state.py)
  lines 28–31 (module docstring).

The module docstring reads: "the remaining mutators (`recount`/`reconcile`) are
later tasks." `recount` is now delivered and is registered as a subcommand in
this very module's `build_app` (lines 280–284), so the docstring contradicts the
code beside it. Only `reconcile` remains a later task.

Proposed fix: narrow the sentence to "the remaining mutator (`reconcile`) is a
later task", and optionally add a clause noting that `recount` is registered here
but delegates to `commands/_recount.py` (mirroring how `set-cursor` and
`advance-phase` delegate to `commands/_state_mutators.py`), so the docstring
inventory of registered subcommands stays accurate.

## Finding 4 — `recount` registration uses a per-call deferred import, unlike its siblings

- Category: inconsistency
- Severity: low
- Location:
  [`commands/novel_state.py`](../../novel_ralph_skill/commands/novel_state.py)
  lines 280–284 (the `recount` command closure) versus lines 244 and 272/277
  (the `mutators` alias path).

`build_app` imports `_state_mutators` once at the top of the builder (line 244,
`from novel_ralph_skill.commands import _state_mutators as mutators`) and the
`set_cursor`/`advance_phase` closures call `mutators.set_cursor(...)` /
`mutators.advance_phase()`. The `recount` closure instead performs its own
`from novel_ralph_skill.commands import _recount` *inside the command body*, so
the import runs on every `recount` invocation rather than once when the app is
built. Both forms dodge the same documented circular import (the builder runs
after both modules are defined), so there is no functional reason for `recount`
to differ; the inconsistency is purely ergonomic and slightly obscures that
`_recount` is a peer of `_state_mutators`.

Proposed fix: import `_recount` alongside `_state_mutators` at the top of
`build_app` (e.g. `from novel_ralph_skill.commands import _recount`) and have the
`recount` closure call `_recount.recount()`, matching the `mutators.*` pattern.
This makes all three load-edit-rewrite mutators register through one consistent
shape and resolves the import once per app build.

## Finding 5 — `_working_dir` lives in `_state_mutators` but is used only by `recount`

- Category: separation-of-concerns
- Severity: low
- Location:
  [`commands/_state_mutators.py`](../../novel_ralph_skill/commands/_state_mutators.py)
  lines 62–70 (`_working_dir`); sole caller
  [`commands/_recount.py`](../../novel_ralph_skill/commands/_recount.py) line 76.

The `recount` slice added `_working_dir` to `_state_mutators.py` and imports it
from there into `_recount.py`. Every *other* shared helper in `_state_mutators`
(`_state_path`, `_load_document_or_state_error`, `_state_view_or_state_error`,
`_refuse_if_incoherent`) is used by two or more mutators, which is why they live
in the shared module. `_working_dir` is currently used by `recount` alone, so its
placement is forward-looking rather than shared-by-use. The docstring even
justifies it in terms of `recount`'s needs. This is defensible (2.3.2's
`reconcile` will plausibly want it, and keeping the cwd-root constants together
is reasonable), so it is noted, not pressed.

Proposed fix: either keep it in `_state_mutators` and add a one-line comment that
it is the shared cwd-root helper anticipating `reconcile` (so a reader does not
read it as a stray single-use export), or move it to `_recount.py` next to its
only caller until a second consumer lands. The comment option is the cheaper of
the two and keeps `_state_path`/`_working_dir` co-located.

## Finding 6 — No unit assertion that `recount` writes a fresh `by_chapter` (key-set shrink case)

- Category: test-gap
- Severity: low
- Location:
  [`commands/_recount.py`](../../novel_ralph_skill/commands/_recount.py) lines
  82–102 and 146 (`_inline_by_chapter`, the in-place table replacement);
  tests in [`test_recount_unit.py`](../../tests/test_recount_unit.py).

`_inline_by_chapter` builds a *fresh* inline table and assigns it over
`document["word_counts"]["by_chapter"]`, which is the mechanism that ensures a
stale key (a chapter dropped from the manifest, or a renumbering) cannot survive
in `by_chapter`. The existing tests all run against a manifest whose key set
matches the prior `by_chapter` (two-chapter trees, or overrides with the same
keys), so the "stale key removed" property — the reason a fresh table is built
rather than mutating the existing one in place — is exercised only incidentally.
No test pins that a prior `by_chapter` carrying an *extra* key the new manifest
omits is dropped after recount.

Proposed fix: add one unit test in `test_recount_unit.py` that seeds a tree whose
hand-typed `by_chapter` carries a key not in the manifest (or a different key set
to the drafts present) and asserts the recounted `by_chapter` equals exactly
the manifest's key set, with no stale entries. This pins the fresh-table rebuild
as a behaviour rather than an implementation incident, and guards against a future
"optimise to in-place update" change silently reintroducing stale keys.
