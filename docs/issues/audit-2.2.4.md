# Post-merge audit — roadmap task 2.2.4

Audit of the codebase after roadmap task 2.2.4 ("Add CLI mutators for the gate
and drafting sub-state") merged to `main` at commit `ac6a8aa`. The slice adds
four `novel-state` subcommands — `set-gate`, `complete-final-pass`,
`set-fangirl`, and `set-critic-pass` — closing the last hand-edit holes in the
harness state (design §4.1, §5.2; ADR 010). `set-gate` is the repair mutator for
a knitting gate that lags its drafted ratio (the §5.2 `gate-ratio-consistent`
invariant binds the three knitting flags); the other three carry small write-time
preconditions checked before the validate-before-persist pass.

The slice is sound, idiomatic, and well covered: unit
([`test_set_gate_unit.py`](../../tests/test_set_gate_unit.py),
[`test_set_fangirl_unit.py`](../../tests/test_set_fangirl_unit.py),
[`test_set_critic_pass_unit.py`](../../tests/test_set_critic_pass_unit.py),
[`test_complete_final_pass_unit.py`](../../tests/test_complete_final_pass_unit.py)),
property
([`test_set_gate_properties.py`](../../tests/test_set_gate_properties.py),
[`test_set_fangirl_properties.py`](../../tests/test_set_fangirl_properties.py),
[`test_set_critic_pass_properties.py`](../../tests/test_set_critic_pass_properties.py)),
registration
([`test_gate_drafting_registration.py`](../../tests/test_gate_drafting_registration.py)),
behavioural ([`complete_final_pass.feature`](../../tests/features/complete_final_pass.feature)),
and installed-binary e2e
([`test_gate_drafting_mutators_e2e.py`](../../tests/test_gate_drafting_mutators_e2e.py)
— exit 0 repair, exit 3 below-threshold refusal, exit 2 no-flag and non-integer,
exit 3 out-of-manifest fangirl, exit 0 final pass). None of the findings below is
a blocking defect; the dominant themes are a recurring usage-error duplication
(now in its second copy), a few consistency gaps against established sibling
patterns (named rule constants, snapshot/BDD parity), and a stale shared-base
docstring.

Trail followed: created a `git-donkey` worktree off `origin/main`
(`git worktree add --detach`), explored with reads over
`commands/_gate_drafting_mutators.py`, `commands/novel_state.py`,
`commands/_state_mutators.py`, `commands/_set_chapters.py`,
`commands/_desloppify.py`, `contract/errors.py`, and `state/validate.py`; traced
history with `git show ac6a8aa` and `git log origin/main`. Source of truth
consulted: `docs/adr-010-gate-drafting-mutators.md`,
`docs/novel-ralph-harness-design.md` §4.1/§5.2, `docs/developers-guide.md`,
`docs/users-guide.md`, `skill/novel-ralph/SKILL.md`,
`skill/novel-ralph/references/state-layout.md`, `AGENTS.md`, and prior
`docs/issues/audit-2.2.2.md` / `audit-2.2.3.md`. Skills loaded: `python-router`.

## Finding 1 — Duplicated usage-error class and exit-2 adapter (second copy)

- Category: duplication
- Severity: medium
- Location:
  [`commands/_gate_drafting_mutators.py:97-110,186-207`](../../novel_ralph_skill/commands/_gate_drafting_mutators.py)
  versus
  [`commands/_desloppify.py:69-80,315-345`](../../novel_ralph_skill/commands/_desloppify.py)

`GateDraftingUsageError(EnvelopeMessagesError)` and its `_set_gate_or_usage`
adapter are a near-verbatim copy of `DesloppifyUsageError` and `_scan_or_usage`.
The class docstrings differ only in the trigger phrase, and the exit-2 mapping
line is now identical in three places:

```python
return CommandOutcome(
    code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or [str(exc)]
)
```

(`_desloppify.py:256-258`, `_desloppify.py:343-345`, and
`_gate_drafting_mutators.py:204-206`). The module docstring openly states it
"copies the proven `_desloppify.DesloppifyUsageError` + `_scan_or_usage`
precedent", so the duplication is deliberate but is now a recurring pattern
across command modules rather than a one-off.

Proposed fix: lift the shared shape into the `contract` layer — a
`BodyUsageError(EnvelopeMessagesError)` base (or a marker) plus a single
`usage_error_outcome(exc: EnvelopeMessagesError) -> CommandOutcome` helper that
both command modules call. Each module keeps its own thin domain subclass for the
docstring-level trigger, but the exit-2 envelope construction lives in exactly
one place, mirroring how `_state_mutators` already centralizes the load/refuse
helpers. Add a unit test pinning the shared helper's envelope.

## Finding 2 — Inline rule-name strings break the named-constant precedent

- Category: inconsistency
- Severity: low
- Location:
  [`commands/_gate_drafting_mutators.py:283-285,331`](../../novel_ralph_skill/commands/_gate_drafting_mutators.py)

`set-fangirl` and `set-critic-pass` are write-time-precondition mutators in the
same family as `set-chapters`, whose module docstring explicitly anchors the
pattern: precondition rule names are declared as `typ.Final` kebab-string
constants gathered in a tuple
([`_set_chapters.py:64-82`](../../novel_ralph_skill/commands/_set_chapters.py):
`CHAPTERS_NON_EMPTY`, `NUMBERS_UNIQUE`, … `MANIFEST_COHERENCE_RULE_NAMES`), so a
refusal "pins exactly the rule broken". The new mutators instead inline the rule
names `fangirl-chapter-in-manifest` and `critic-pass-at-least-one` directly in
the f-string `summary` of each body, with the same string also appearing in the
ADR/guide prose. There is no single source for the name, so a rename drifts
silently and no test can assert against a shared constant.

Proposed fix: hoist the two rule names to module-level `typ.Final` constants
(e.g. `FANGIRL_CHAPTER_IN_MANIFEST`, `CRITIC_PASS_AT_LEAST_ONE`), reference them
in the refusal summaries, and assert against them in the unit tests, matching the
`_set_chapters` precedent.

## Finding 3 — Snapshot coverage asymmetry across the four mutators

- Category: test-gap
- Severity: low
- Location:
  [`tests/test_set_gate_snapshots.py`](../../tests/test_set_gate_snapshots.py)
  and absent peers

The sibling mutator baseline pins *both* a success and a refusal envelope
snapshot per mutator
([`test_novel_state_mutator_snapshots.py`](../../tests/test_novel_state_mutator_snapshots.py)
covers `set-cursor` success + refusal, `advance-phase` success + refusal,
`recount` success). Task 2.2.4 pins only a single `set-gate` *success* `result`
snapshot. There is no refusal snapshot for `set-gate` and no snapshot at all for
`complete-final-pass`, `set-fangirl`, or `set-critic-pass`, so the exact
write-shaped `result` and the exit-3 refusal envelope of three of the four new
mutators are unpinned. Behaviour is still asserted semantically in the unit and
e2e suites, so this is a regression-protection gap, not a correctness gap.

Proposed fix: add success (and where applicable refusal) `result`/envelope
snapshots for `complete-final-pass`, `set-fangirl`, and `set-critic-pass`, plus
a `set-gate` below-threshold refusal snapshot, matching the sibling-mutator parity
in `test_novel_state_mutator_snapshots.py`.

## Finding 4 — BDD coverage only for `complete-final-pass`

- Category: test-gap
- Severity: low
- Location: [`tests/features/`](../../tests/features/) (only
  `complete_final_pass.feature` added)

Of the four new verbs only `complete-final-pass` gained a `.feature` /
behavioural suite. `set-gate` carries the slice's most interesting observable
behaviour — the incoherent→coherent ratio repair, the below-threshold refusal,
and the no-flag exit-2 usage arm — yet has no behavioural scenario, where
comparable sibling repair/refusal verbs do (`advance_phase_refusal.feature`,
`reconcile.feature`, `recount.feature`, `set_chapters.feature`). The e2e suite
exercises these arms, so coverage exists, but the operator-readable behavioural
specification of the headline mutator is missing.

Proposed fix: add a `set_gate.feature` covering the three operator-visible arms
(repair to exit 0, below-threshold refusal to exit 3, no-flag usage error to exit
2), consistent with the behavioural specs for the other refusal-bearing mutators.

## Finding 5 — Stale `EnvelopeMessagesError` docstring (now omits four subclasses)

- Category: docs-gap
- Severity: low
- Location:
  [`contract/errors.py:22-28`](../../novel_ralph_skill/contract/errors.py)

The shared base's docstring states it is subclassed by "the three domain
exceptions" and names `StateInputError`, `RulePackError`, and `RulePackFileError`.
The codebase now has seven subclasses: those three plus `LedgerError`,
`LedgerFileError`, `DesloppifyUsageError`, and — added by this slice —
`GateDraftingUsageError`. The count and the enumeration are both stale; 2.2.4
widens the gap by adding the fourth uncounted subclass without touching the base
docstring.

Proposed fix: replace the brittle hand-maintained enumeration with a
count-agnostic phrasing (e.g. "the domain error types across the `contract`,
`ledger`, `rulepack`, and command layers subclass it") so the docstring does not
require an edit every time a new subclass lands.

## Finding 6 — Two command-registration idioms now coexist on one app

- Category: separation-of-concerns
- Severity: low
- Location:
  [`commands/novel_state.py:350-398`](../../novel_ralph_skill/commands/novel_state.py)
  and
  [`commands/_gate_drafting_mutators.py:345-399`](../../novel_ralph_skill/commands/_gate_drafting_mutators.py)

`build_app` registers six subcommands as inline `@app.command` wrappers
(`check`, `init`, `set-cursor`, `advance-phase`, `recount`, `reconcile`,
`set-chapters`), but delegates the four gate/drafting verbs to an external
`register_gate_drafting_commands(app)` registrar. The split was introduced to
keep `novel_state.py` under the 400-line cap (Decision D11/B4), which is a sound
motive, but the result is two registration patterns for the same app: a reader
must now know that "the subcommands of `novel-state`" live in two files under two
idioms.

Proposed fix: this is acceptable as a size-driven trade-off, but consider, when
a further mutator family lands, normalizing on the registrar pattern (one
`register_*` per mutator family, `build_app` becoming a thin sequence of registrar
calls) so the app has a single, uniform wiring idiom rather than a mix.

## Finding 7 — Two command modules sit exactly at the 400-line ceiling

- Category: complexity
- Severity: low
- Location:
  [`commands/novel_state.py`](../../novel_ralph_skill/commands/novel_state.py)
  (399 lines) and
  [`commands/_gate_drafting_mutators.py`](../../novel_ralph_skill/commands/_gate_drafting_mutators.py)
  (399 lines)

AGENTS.md caps a single code file at 400 lines. Both modules now sit at 399 —
one line under the cap. The registrar split was meant to relieve `novel_state.py`,
yet the new module landed at the same ceiling, so *both* files are now maximally
full. Any further line in either (a new mutator, a longer docstring, an extra
import) breaches the cap and forces an unplanned split mid-change.

Proposed fix: pre-emptively create headroom before the next mutator slice — e.g.
move the four `@app.command` wrapper bodies' shared boilerplate, or extract the
`set-gate` `GateSelection`/`_apply_gate_edits` pair into a small leaf module —
so neither file is a single edit away from the cap.

## Finding 8 — Structural-completeness view named inconsistently across bodies

- Category: ergonomics
- Severity: low
- Location:
  [`commands/_gate_drafting_mutators.py:174,244,280,329`](../../novel_ralph_skill/commands/_gate_drafting_mutators.py)

Every body derives the typed view once to prove the document is structurally
complete before editing. `_set_fangirl` binds it (`prior = ...`) because it needs
`len(prior.chapters)`; the other three call `_state_view_or_state_error(document)`
and discard the result for its side effect of raising on an incomplete document.
The discard-for-side-effect call reads as a no-op to a casual reader and relies
on a comment (present only in `_set_gate`) to explain why it is not dead code.

Proposed fix: extract a small named helper in `_state_mutators`, e.g.
`_assert_structurally_complete(document) -> None`, that the discard sites call,
making the intent ("prove completeness, keep the document as the write source")
self-documenting and removing the four bare expression-statements. `_set_fangirl`
keeps its binding form because it consumes the view.
