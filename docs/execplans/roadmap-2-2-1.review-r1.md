# Adversarial Logisphere design review — roadmap 2.2.1 (round 1)

Target: `docs/execplans/roadmap-2-2-1.md` ("Implement the `tomlkit` round-trip
and atomic write helper"). Status of plan at review: DRAFT.

Verdict: **Revise.** The plan is well-grounded against ADR-002, design
§3.4/§5.3, the scripting standards, and AGENTS.md, and its non-shell-out /
no-cuprum stance is correctly cited. But its central acceptance criterion does
not test the capability the design actually buys, and two contract seams are
under-specified. These go back to the planner.

## Verified claims (held up against source)

- `tomlkit` is locked at 0.15.0 (`uv.lock` lines 667-672).
  `requires-python = ">=3.14"`, deps `cyclopts`, `tomlkit` (`pyproject.toml`).
  Confirmed.
- Atomic-write pattern
  (`tempfile.NamedTemporaryFile("w", delete=False, dir=parent, ...)` then
  `Path.replace`) matches `docs/scripting-standards.md`
  §"Reading / writing files and atomic updates" lines 409-414 exactly.
- `PendingTurn` schema fields are `operation: str` and `paths: tuple[str, ...]`
  (`state/schema.py` 264-280). Plan's `open_pending_turn(operation, paths)`
  matches.
- `parse_state` reads an optional `pending_turn` via `raw.get("pending_turn")`
  and `_pending_turn` (parse.py 175-224). The plan's `document_to_state`
  delegation is sound.
- The state package and `parse.py` docstrings promise read-only and explicitly
  defer writing to "task 2.2.1" (parse.py 9, `__init__.py` 11). The decision to
  add a new `document.py` rather than extend `parse.py` is correct.
- No-shell-out / no-cuprum: design §4 line 241 says cuprum is required only
  where a command shells out, and none do in v1. Plan cites this correctly.
- `make all` gate components (Ruff, interrogate 100%, Pylint, ty, pip-audit)
  match AGENTS.md lines 81-92. The `xfail`-at-commit tactic keeps the red
  scaffold gate-green and is consistent with AGENTS.md "gate green at commit".

## Blocking defects

### B1 — The round-trip property is validated over a comment-free corpus, so it does not test comment/layout preservation (the entire point of ADR-002)

The plan's primary acceptance criterion (work item 1, work item 2 green, and
the "Validation and acceptance" section) is the Hypothesis property:
`tomlkit.dumps(load_document(p)) == original_bytes_decoded`, drawn over the
corpus trees (`coherent_oracle_cases` / `phase_state_tree` / `baseline_tree`).

But the corpus `state.toml` files are built programmatically by
`tests/working_corpus/_builder.py` via `tomlkit.table()` / `inline_table()` and
`tomlkit.dumps(...)` — they contain **zero comments and no hand-authored
layout** (`_build_state_document`, lines 134-154; no comment insertion anywhere
in the builder). A byte-for-byte no-op property over comment-free, tomlkit-
emitted files proves only that `parse → dumps` is identity on tomlkit's own
output. It would pass unchanged even if `load_document`/
`write_document_ atomically` silently stripped comments, reflowed tables, or
dropped inline comments — because there is nothing in the corpus to strip.

ADR-002 Functional requirement 1 is "a no-op read-mutate-write preserves the
file byte-for-byte, **including comments and whitespace**." Design §5.3 and
§5.2 of ADR-002's risk note name the round-trip property as the guard against a
silent tomlkit regression. As specified, the property does not guard that: a
tomlkit major-version change that broke comment round-tripping would not be
caught, because the corpus has no comments to lose. The plan even acknowledges
in "Surprises & discoveries" that the *real* preservation evidence came from "a
realistic multi-table `state.toml`" probe with block and inline comments — yet
that comment-bearing artefact is demoted to a single non-property unit example,
while the property (the thing design §9 calls the guard) runs only over the
comment-free corpus.

Required fix: the round-trip **property** (not just one example) must exercise
at least one comment-and-layout-bearing `state.toml` fixture — a hand-authored
corpus file with block comments, inline comments, blank-line layout, and at
least one inline/array-of-tables form — so the byte-for-byte assertion actually
constrains comment and whitespace preservation. Either add such a fixture to
the corpus (preferred, since later tasks reuse it) or have the property draw
over a small set of hand-authored comment-bearing documents. The comment-free
corpus sweep may remain as an additional case, but it cannot be the sole
carrier of the ADR-002 round-trip guarantee.

### B2 — Comment/whitespace preservation under a *value mutation* is asserted only by a single example, not against the corpus, and the §5.3 "no-op recount preserves formatting and comments" criterion is left unverified

Design §9 names specifically: "a no-op `recount` preserves formatting and
comments." A recount mutates `word_counts.current` (and `by_chapter`). The
plan's surgical-mutation coverage (work item 2) is "a property or example test"
on a corpus document asserting "all other tables equal and the comment text is
preserved" — but the corpus documents have **no comments** (see B1), so "the
comment text is preserved" is vacuously true there, and the one comment-bearing
check is again a lone hand-authored example, not the property design §9 calls
for. The "surgical value mutation rewrites only the value's bytes and preserves
both block and inline comments" claim in Surprises & discoveries is exactly the
thing that must be pinned by a test over a comment-bearing input, not asserted
from an ambient probe at tomlkit 0.14.0 (the locked version is 0.15.0; see B3).

Required fix: pin the surgical-mutation comment-preservation property against a
comment-bearing fixture so the "no-op recount preserves formatting and
comments" acceptance is genuinely tested at the locked tomlkit version.

### B3 — The empirical round-trip probe was run at tomlkit 0.14.0, but the locked version is 0.15.0; the cross-version equivalence is asserted from memory, not verified

"Surprises & discoveries" and "Artifacts and notes" record the probe results
(NOOP_BYTE_IDENTICAL, VALUE_MUTATION_SURGICAL, the add-then-remove whitespace
artefact) at **tomlkit 0.14.0 ambient**, then assert "locked 0.15.0 behaves
identically per the official quickstart." That is an uncited, memory-based
equivalence claim across a minor version — precisely the class of claim this
review must treat as blocking. The whole point of the round-trip property
(ADR-002 "Known risks") is to catch a tomlkit version regression; the plan's
own evidence base was gathered on a *different* version than the one that ships.

Required fix: either (a) re-run the probe under the project's `uv`-resolved
environment (tomlkit 0.15.0) and record those results, or (b) state plainly
that the property test at 0.15.0 is the verification and remove the "behaves
identically" assertion, ensuring the comment-bearing property from B1/B2 runs
at 0.15.0 so the version actually shipped is the version pinned. The 0.15.0
quickstart claim, if cited, should be fetched from the official 0.15.0 docs,
not recalled.

## Advisory (non-blocking, but address)

### A1 — The `pending_turn` context manager's write-source on clean exit is under-specified, and 2.2.2 mutators depend on it

The contract yields the live `TOMLDocument` "for the caller's artefact work,"
then "clear[s] the record and write[s] atomically on clean exit." A real
mutator (e.g. `recount`) will mutate state *values* on that yielded document
during the turn (updating `word_counts`), not only write sibling files. The
plan does not state whether the final clear-and-write re-dumps the
*caller-mutated* document (preserving those value edits) or reloads/operates on
a fresh copy. If it reloads, the caller's in-turn value edits are lost; if it
re-dumps the mutated document, that must be stated as the contract so 2.2.2
builds on it correctly. Make the "yielded document is the single write source
for the clean-exit write" explicit in the interface contract.

### A2 — §5.4 rollback semantics: "leaves state.toml at the prior coherent point" vs. a populated record on disk

Design §5.4 says rolling back "clears the `[pending_turn]` record and leaves
`state.toml` at the prior coherent point," and that completing vs. rolling back
is `reconcile`'s job (task 2.3.2), not this helper's. The plan's interrupted-
write behaviour (leave the populated record on disk for the next turn) is the
correct *producer* side and matches §3.4/§10. This is fine — but the plan
should note explicitly that producing the uncleared record is all this task
owns, and that "prior coherent point" recovery on rollback is 2.3.2's, so a
reviewer does not mistake the missing rollback path for a gap here. The
"clear-restores" property (parsed-equality) is the right strength; just
signpost the boundary.

### A3 — "tree fixture returns a path with state.toml at its root" is loosely stated

The corpus fixtures (`phase_state_tree`, `baseline_tree`) are **factory
callables** returning the `working/` directory path; `coherent_oracle_cases`
returns `(spec, working_dir)` pairs (`corpus_fixtures.py` 125-203). The plan's
prose ("a tree fixture materialises a `working/` directory … with
`state.toml` at its root") is close but elides that these are callables and
that the state file is at `working_dir / "state.toml"`. Minor, but the
implementer should not expect a bare `Path` fixture; tighten the wording so the
test reads `(working_dir / "state.toml").read_text()` from the factory's return.

## Pre-mortem (Doggylump leads)

Six months on, a tomlkit 0.15.x → 0.16 bump lands in a routine `uv lock`
refresh. It quietly changes how a trailing blank line after the last table is
emitted. The round-trip property is green — because it only ever ran over the
comment-free, tomlkit-emitted corpus, whose output already matches the new
emitter. The first real `state.toml` with hand-authored recovery comments gets
its comment block reflowed on the next `recount`; a maintainer reading the file
during a 03:00 recovery finds the layout they relied on has drifted. The signal
the team missed: the guard test was structurally incapable of seeing comment
loss. Mitigation is B1/B2 — make the property carry a comment-bearing input.

Second scenario: a mutator in 2.2.2 wraps a value edit in `pending_turn`,
mutates `word_counts` on the yielded document, exits cleanly — and the edit
vanishes because the clean-exit write reloaded a fresh document before
clearing. Caught only in integration. Mitigation is A1 — pin the write-source
contract and add a test that a value mutation made inside the bracket survives
a clean exit.

## Strongest alternative (Wafflecat)

The plan reserves byte-for-byte for no-op and surgical-value edits and drops to
parsed-`State` equality for the `[pending_turn]` open/clear cycle, because
tomlkit add-then-remove leaves a residual blank line. A viable alternative:
model `[pending_turn]` so the open/clear cycle *is* byte-reversible — e.g.
reserve the table's position with a stable, always-present sentinel layout
(empty table kept in place, fields added/removed rather than the whole table
inserted/deleted), so clearing restores the exact prior bytes. Trade-off: it
complicates the `state.toml` baseline layout (a permanently-present
`[pending_turn]` shell) and leaks a writer concern into the §5.1 schema, which
the design did not ask for. The plan's choice (two deliberately-different
property strengths) is the lower- risk option and is well justified; the
alternative is noted only to confirm the chosen split is the right call. No
change required on this axis.

## Required next steps (ordered)

1. B1: make the no-op round-trip **property** carry a comment-and-layout-bearing
   `state.toml` fixture; do not let the comment-free corpus be the sole input.
2. B2: pin the surgical-mutation comment-preservation as a property over a
   comment-bearing input (the §9 "no-op recount preserves comments" criterion).
3. B3: re-run/record the round-trip probe at the locked tomlkit 0.15.0, or
   replace the "behaves identically" memory claim with the 0.15.0 property test
   as the verification; cite official 0.15.0 docs if quoting them.
4. A1: state the clean-exit write-source contract for the `pending_turn` bracket
   and add a test that an in-bracket value edit survives a clean exit.
5. A2/A3: signpost the §5.4 producer/consumer boundary and tighten the fixture
   wording.

Trail followed: ADR-002; design §3.4, §5.1, §5.2, §5.3, §5.4, §9, §10;
`docs/scripting-standards.md` §"Reading / writing files and atomic updates";
AGENTS.md "Change quality and committing" / testing rules; `state/parse.py`,
`state/schema.py`, `state/__init__.py`; `tests/working_corpus/_builder.py`;
`tests/corpus_fixtures.py`; `tests/test_state_layout_reference.py`; cuprum
read-only checkout (`cuprum/program.py`, `cuprum/sh.py`); `uv.lock`,
`pyproject.toml`.
