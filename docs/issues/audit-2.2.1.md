# Post-merge audit — roadmap task 2.2.1

Audit of the codebase after roadmap task 2.2.1 ("Implement the tomlkit
round-trip and atomic write helper") merged to `main` at commit `f953082`. The
slice delivers the write half of the `state` slice in
[`novel_ralph_skill/state/document.py`](../../novel_ralph_skill/state/document.py):
a lossless `tomlkit` round-trip (`load_document`, `document_to_state`), an
atomic temp-file-plus-`Path.replace` writer (`write_document_atomically`), and
the `[pending_turn]` intent bracket (`open_pending_turn`, `clear_pending_turn`,
and the `pending_turn` context manager). It is re-exported from
[`novel_ralph_skill/state/__init__.py`](../../novel_ralph_skill/state/__init__.py),
documented in the developers' guide, and guarded by
[`tests/test_state_document.py`](../../tests/test_state_document.py) plus the
torn-turn behavioural scenario
([`tests/features/torn_turn.feature`](../../tests/features/torn_turn.feature),
[`tests/steps/torn_turn_steps.py`](../../tests/steps/torn_turn_steps.py)).

The slice is sound and discharges its success criterion: a no-op write
round-trips byte-for-byte, a surgical value edit rewrites only the touched
bytes, the atomic write leaves the prior file untorn on failure, and a bracket
that dies mid-turn leaves a populated `[pending_turn]` for the next turn's
`reconcile`. The lossless-versus-typed boundary (the document is the write
source, the typed `State` is a read view only) is implemented and explained
exactly as ADR-002 and the design Decision Log require.

This audit checks the new write module against the design's authoritative
artefacts and the recurring themes carried by the prior audits
(`docs/issues/audit-1.2.1.md` through `docs/issues/audit-1.3.2.md`). Each
finding records a category, a location, a description, a concrete proposed fix,
and a severity. None is a blocking defect; they are tidy-up and coverage
opportunities.

Trail followed: explored with `leta`/`Read` over `document.py`, `parse.py`,
`state/__init__.py`, the corpus builder, and the tests; traced history with
`git log origin/main` and `sem`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §3.4, §5.1, §5.3, and §9;
[`docs/adr-002-toml-round-trip-tomlkit.md`](../adr-002-toml-round-trip-tomlkit.md);
[`docs/adr-001-deterministic-judgemental-boundary.md`](../adr-001-deterministic-judgemental-boundary.md);
`docs/scripting-standards.md`; `docs/developers-guide.md`; and `AGENTS.md`.
Language router: `python-router` (Python boundary constructors, context
managers, atomic-write idioms).

## Finding 1 — Two hand-authored `state.toml` fixtures duplicate the same schema shape

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`tests/test_state_document.py:47-102`](../../tests/test_state_document.py)
  (`COMMENT_BEARING_STATE_TOML`) and
  [`tests/steps/torn_turn_steps.py:36-81`](../../tests/steps/torn_turn_steps.py)
  (`_SETTLED_STATE_TOML`)

The 2.2.1 slice introduces two large, hand-authored `state.toml` string
literals that carry the *same* novel ("The Lantern Keeper", slug
`the-lantern-keeper`, `target_word_count = 80000`, `created_at`
`2026-06-22T09:00:00Z`) and the same table skeleton, differing only in a few
values (`COMMENT_BEARING_STATE_TOML` has two `[[chapters]]` and richer comment
layout; `_SETTLED_STATE_TOML` has one chapter and `completed = ["premise"]`).
Both must stay schema-aligned with
[`novel_ralph_skill/state/schema.py`](../../novel_ralph_skill/state/schema.py)
and `parse_state` by hand. A schema change (a new required table or key) must be
mirrored in both literals or one suite silently tests a stale shape. The
comment-bearing literal genuinely cannot come from the corpus builder (the
builder emits no comments, which is the documented reason the round-trip
property uses a hand-authored carrier — ExecPlan round-1 review B1/B2). But
`_SETTLED_STATE_TOML` is comment-free, so it overlaps both the
comment-bearing literal *and* the comment-free baseline the corpus builder
([`tests/working_corpus/_builder.py`](../../tests/working_corpus/_builder.py),
exposed as the `baseline_tree` fixture) already produces.

**Proposed fix:** retire `_SETTLED_STATE_TOML` and drive the torn-turn scenario
from the existing `baseline_tree` corpus fixture (or `coherent_oracle_cases`),
which builds a schema-valid comment-free `working/` tree through the same
`tomlkit` builder the rest of the suite trusts. If a literal is unavoidable for
the comment-bearing property, derive the single shared identity (novel title,
slug, `created_at`) from one named constant so a schema or identity change has
one edit site. `make test`/`make markdownlint` are unaffected; this is a
test-refactor change gated by Ruff and `pytest`.

## Finding 2 — `_TEMP_PREFIX` hard-codes `state.toml` while the writer is path-generic

- **Category:** inconsistency
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/state/document.py:54-57`](../../novel_ralph_skill/state/document.py)
  and `write_document_atomically` (lines 114-151)

`write_document_atomically(document, path)` accepts an arbitrary target `path`
and is documented as the generic atomic writer the whole `state` slice composes,
but the in-directory temporary file is always prefixed `.state.toml.`
(`_TEMP_PREFIX = ".state.toml."`). If a later mutator reuses this helper to
write any file other than `state.toml` (the helper's signature invites that),
the leaked-temp-file recognisability the prefix is meant to provide (Risk
"atomic temp file leaks") names the wrong file, and a directory holding two such
writes would collide on the same recognizable prefix. The prefix couples a
generic mechanism to one specific filename.

**Proposed fix:** derive the prefix from the target, for example
`prefix=f".{path.name}."`, so the recognizable temp name always tracks the file
being written; keep the trailing `.tmp` suffix. Update the docstring note and
the leaked-temp assertion in
[`test_atomic_write_leaves_prior_file_and_no_temp_on_failure`](../../tests/test_state_document.py)
if it keys on the literal prefix. Alternatively, if the helper is intended to
remain `state.toml`-only, narrow the docstring and parameter name to say so.
Gated by Ruff, `pyright`, and `pytest`.

## Finding 3 — The documented "parent must already exist" precondition is neither guarded nor tested

- **Category:** test-gap
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/state/document.py:114-151`](../../novel_ralph_skill/state/document.py)
  (docstring line 128: "Its parent must already exist")

`write_document_atomically`'s docstring states the target's parent must already
exist, because the temp file is created with `dir=path.parent`. If a caller
passes a path whose parent is absent, `tempfile.NamedTemporaryFile` raises
`FileNotFoundError` from inside the helper rather than a domain-meaningful error,
and no test pins this contract — so the failure mode is undocumented at the
exit-code boundary task 2.2.x will own. The other failure path (a `Path.replace`
that raises) is tested thoroughly
([`test_atomic_write_leaves_prior_file_and_no_temp_on_failure`](../../tests/test_state_document.py:269)),
which makes the missing parent case the one untested edge of the writer.

**Proposed fix:** add a small unit test asserting the behaviour when
`path.parent` is absent (either that it raises a recognizable error, or — if the
slice prefers — that the helper creates the parent), and align the docstring
with whichever behaviour is chosen. This documents the precondition at the seam
where the §5.2 validator and the CLI (tasks 2.1.2, 2.2.2) will rely on it.
Gated by `pytest` and `interrogate`.

## Finding 4 — `open_pending_turn` re-implements list population instead of constructing the array directly

- **Category:** ergonomics
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/state/document.py:175-179`](../../novel_ralph_skill/state/document.py)

`open_pending_turn` builds the `paths` array in three statements — create an
empty single-line `tomlkit` array, then `extend` it from the caller's sequence:

```python
record["paths"] = tomlkit.array().multiline(multiline=False)
record["paths"].extend(paths)
```

The two-step create-then-extend pattern reads as imperative scaffolding around
what is conceptually one value, and the second statement subscripts the record
again to reach the array it just set. `tomlkit.array()` accepts the items
directly (`tomlkit.array(list(paths))` or `tomlkit.item(list(paths))`), which
expresses the intent — "the paths array is this sequence" — in one statement and
still copies into a fresh `tomlkit` array so the document does not alias the
caller's sequence (the aliasing guarantee the `Notes` section promises).

**Proposed fix:** construct the array in one expression, for example
`record["paths"] = tomlkit.array(list(paths))` (verifying the single-line vs
multiline rendering the round-trip tests expect), dropping the separate
`extend`. Keep the `Notes` paragraph about copying so the no-alias contract
stays documented. Gated by Ruff and `pytest` (the existing
`test_open_pending_turn_round_trips_through_schema` covers the behaviour).
