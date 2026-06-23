# Post-merge audit — roadmap task 2.2.2

Audit of the codebase after roadmap task 2.2.2 ("Implement novel-state init,
set-cursor, and advance-phase mutators") merged to `main` at commit `141472a`.
The slice lands the three *write* mutators of `novel-state`: `init` (the create
mutator, in
[`commands/novel_state.py`](../../novel_ralph_skill/commands/novel_state.py)),
and `set-cursor` plus `advance-phase` (the load-edit-rewrite mutators, in
[`commands/_state_mutators.py`](../../novel_ralph_skill/commands/_state_mutators.py)).
Each loads `working/state.toml` through the `tomlkit` round-trip, validates the
proposed state against the §5.2 invariants before persisting, and refuses an
incoherent transition with exit `3`, leaving `state.toml` byte-for-byte intact.

The slice is sound and well covered: the contract tests
([`test_novel_state_mutators.py`](../../tests/test_novel_state_mutators.py))
exercise every success and refusal path through the shared `run` wrapper, a
Hypothesis property pins the `set-cursor`-versus-validator equivalence
([`test_state_mutators_unit.py`](../../tests/test_state_mutators_unit.py)), and
a `pytest-bdd` scenario proves the out-of-order `advance-phase` refusal
([`test_advance_phase_bdd.py`](../../tests/test_advance_phase_bdd.py)). None of
the findings below is a blocking defect. The dominant theme is a *user-docs gap*:
2.2.2 shipped three user-facing subcommands and updated the developers' guide but
left the users' guide describing only `novel-state check`.

Trail followed: explored with `leta`/reads over `commands/novel_state.py`,
`commands/_state_mutators.py`, `state/document.py`, `state/validate.py`,
`contract/runner.py`, and the 2.2.2 test modules; traced history with
`git show 141472a` and `git log origin/main`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §3.2/§4.1/§5.2, `docs/users-guide.md`,
`docs/developers-guide.md` "State mutators", prior `docs/issues/audit-2.1.2.md`
and `audit-2.2.1.md`, and `AGENTS.md`. Each finding records a category, a
location, a description, a concrete proposed fix, and a severity.

## Finding 1 — Users' guide documents only `check`; `init`, `set-cursor`, and `advance-phase` are undocumented

- Category: docs-gap
- Severity: high
- Location:
  [`docs/users-guide.md`](../../docs/users-guide.md) lines 92–128 (the
  `novel-state` section).

Task 2.2.2 promoted three subcommands from stubs to shipping commands, but the
users' guide still says only "`novel-state` now has its first real subcommand,
`novel-state check`" and documents nothing about `init`, `set-cursor`, or
`advance-phase`. The grep `set-cursor|advance-phase|init` over `users-guide.md`
finds no operational description of any of them. The developers' guide *was*
updated (it gained a 50-line "State mutators" section), so the omission is
purely user-facing. A user reading the guide cannot learn that `init`
bootstraps `working/`, that `set-cursor` takes `--chapter/--scene/--beat`, or
that any of the three refuses an incoherent transition with exit `3` and writes
nothing.

Proposed fix: extend the `novel-state` section of `users-guide.md` with a
subcommand each for `init` (its `--title/--slug/--target-word-count` options,
the directory skeleton it creates, and the exit-`3` refusal to overwrite an
existing `state.toml`), `set-cursor` (its three integer options and the
`cursor-coherent` refusal), and `advance-phase` (its zero-argument advance, the
terminal-`done` refusal, and the empty-manifest-into-`drafting` refusal). State
the shared "validate-before-persist, refuse with exit `3`, write nothing"
contract once and reference it from each.

## Finding 2 — Successful mutators emit a read-shaped `result.violations: []` payload

- Category: cqs
- Severity: medium
- Location:
  [`commands/_state_mutators.py`](../../novel_ralph_skill/commands/_state_mutators.py)
  lines 206–210 (`set_cursor`) and 286–292 (`advance_phase`).

Both write mutators return `result={"violations": []}` on a successful write.
That payload is the read shape `novel-state check` emits (`_check` in
[`novel_state.py`](../../novel_ralph_skill/commands/novel_state.py) line 156
returns `{"violations": [...]}`). Emitting an empty `violations` list from a
*command* (a write that mutated `state.toml`) borrows the vocabulary of a
*query* (the checker that reports invariant breaches and writes nothing),
blurring the §5.4 checker/mutator split the design is careful to keep clean. It
is also internally inconsistent: the third mutator, `init`, returns a meaningful
write result (`{"working_dir", "slug"}` at line 212), not a `violations` echo.
An agent parsing the envelope cannot tell from `result` alone whether it ran a
checker or a mutator, and an empty `violations` list on a write result invites
the misreading "this command checked invariants and found none".

Proposed fix: give the two write mutators a write-shaped `result` — e.g.
`set-cursor` returns the cursor it set (`{"current_chapter", "current_scene",
"current_beat"}`) and `advance-phase` returns the transition (`{"from", "to"}`)
— and drop the `violations` key from mutator success results, reserving that key
for the `check` query. If a uniform field is wanted across all `novel-state`
subcommands, define it deliberately in the design/developers' guide rather than
letting `check`'s read shape leak into the mutators by copy.

## Finding 3 — `working/state.toml` path is constructed in three places; the helper that exists is used by only two call sites

- Category: duplication
- Severity: low
- Location:
  [`commands/novel_state.py`](../../novel_ralph_skill/commands/novel_state.py)
  line 146 (`_check`) and line 192 (`_init`); the helper
  [`commands/_state_mutators.py`](../../novel_ralph_skill/commands/_state_mutators.py)
  lines 57–59 (`_state_path`).

`_state_mutators._state_path()` exists to centralise the fixed cwd-relative
`working/state.toml` path and is used by `set_cursor` and `advance_phase`. But
`_check` re-derives the same path inline as
`pathlib.Path(WORKING_DIR_NAME) / "state.toml"` (line 146) and `_init` builds it
as `working / "state.toml"` (line 192). Three independent constructions of one
canonical path mean a future change to the layout (or a `--working-dir` flag, if
the design ever adds one — it currently forbids it) must be made in three
places, and a partial edit would silently let one subcommand read a different
file from the others.

Proposed fix: promote a single shared path accessor (or reuse `_state_path`)
and route `_check` and `_init` through it. Since `_state_path` lives in the
mutator module that imports *from* `novel_state` (to avoid the circular import
the builder already works around), the cleaner home is `novel_state.py` itself:
define the path helper there next to `WORKING_DIR_NAME` and have
`_state_mutators` import it alongside `WORKING_DIR_NAME` and `STATE_INPUT_ERRORS`.

## Finding 4 — `advance-phase`'s empty-manifest-into-`drafting` precondition has only a contract test, no behavioural or property proof

- Category: test-gap
- Severity: low
- Location:
  [`commands/_state_mutators.py`](../../novel_ralph_skill/commands/_state_mutators.py)
  lines 278–280 (the `Phase.DRAFTING and not prior.chapters` guard);
  [`tests/test_novel_state_mutators.py`](../../tests/test_novel_state_mutators.py)
  line 263 (`test_advance_phase_refuses_empty_manifest_into_drafting`).

The §4.1 precondition that advancing into `drafting` requires a populated
chapter manifest is a refusal the §5.2 validator does *not* own (the docstring
notes this explicitly), so it is a hand-coded guard with no oracle behind it. It
has exactly one example-based contract test. By contrast `set-cursor` has a
Hypothesis property tying it to the validator oracle, and the out-of-order
`advance-phase` refusal has a `pytest-bdd` scenario. The manifest precondition —
the one `advance-phase` rule with no validator twin — has the thinnest coverage
of the three refusal classes, so a regression that dropped or inverted the
`not prior.chapters` guard would be caught only by that single example.

Proposed fix: add a focused test that asserts the symmetric positive case (an
advance into `drafting` *succeeds* once the manifest is populated) alongside the
existing empty-manifest refusal, so the guard is pinned from both sides. A
`pytest-bdd` scenario mirroring `advance_phase_refusal.feature` would also make
this design §4.1 precondition a first-class behavioural proof rather than an
implementation-level unit case.

## Finding 5 — `rulepack/parse.py` exceeds the 400-line file cap (pre-existing, not introduced by 2.2.2)

- Category: complexity
- Severity: low
- Location:
  [`novel_ralph_skill/rulepack/parse.py`](../../novel_ralph_skill/rulepack/parse.py)
  (515 lines).

AGENTS.md "Keep file size manageable" caps a single code file at 400 lines.
`rulepack/parse.py` is 515 lines: a flat run of single-key validation helpers
(`_require`, `_require_str`, `_require_int`), pattern/basis/page-words resolvers,
and the `_rule`/`parse_rulepack`/`load_rulepack` assembly. Task 2.2.2 did not
touch this file, so this is a pre-existing overflow surfaced by the audit, not a
regression. It is flagged so the cap breach is recorded rather than normalised.

Proposed fix: split the scalar-coercion helpers (`_where`, `_reject_unknown_keys`,
`_require`, `_require_str`, `_require_int`, `_entries`) into a sibling
`rulepack/_coerce.py` (or `_fields.py`) leaf module, leaving `parse.py` holding
the rule-level resolvers and the public `parse_rulepack`/`load_rulepack` entry
points. This colocates the field-coercion vocabulary and brings both files under
the cap without changing behaviour.

## Summary

The 2.2.2 mutator slice is correct, refuses incoherent transitions on the
exit-`3` channel as the design demands, and is thoroughly tested at the contract,
property, and behavioural levels. The actionable gaps are documentation and
consistency rather than defects: the users' guide must catch up with the three
shipped subcommands (Finding 1, highest value), the write mutators should stop
echoing the checker's `violations` shape (Finding 2), the canonical state path
should have one home (Finding 3), and the manifest precondition deserves a
positive-case and ideally behavioural proof (Finding 4). Finding 5 is a
pre-existing file-size cap breach recorded for completeness.
