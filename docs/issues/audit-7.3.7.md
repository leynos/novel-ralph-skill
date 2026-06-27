# Post-merge audit — roadmap task 7.3.7

Audit of the codebase after roadmap task 7.3.7 ("Centralise the body-detected
usage-error (exit-2) envelope") merged to `main` at commit `7b3ed2f`. The slice
lifts the duplicated exit-`2` usage-error envelope into a single contract-layer
home. It adds a
[`BodyUsageError(EnvelopeMessagesError)`](../../novel_ralph_skill/contract/errors.py)
marker base and a
[`usage_error_outcome(exc)`](../../novel_ralph_skill/contract/runner.py) helper
that builds the exit-`2`
`CommandOutcome(code=ExitCode.USAGE_ERROR, messages=…)` once; reroutes the
`set-gate` adapter
([`_set_gate_or_usage`](../../novel_ralph_skill/commands/_gate_drafting_mutators.py)),
the `desloppify` adapter
([`_scan_or_usage`](../../novel_ralph_skill/commands/_desloppify.py)), and the
ledger arm
([`ledger_scan`](../../novel_ralph_skill/commands/_desloppify_ledger.py)) through
the shared helper; keeps a thin domain subclass per module
(`DesloppifyUsageError`, `GateDraftingUsageError`); and adds a structural
single-home guard
([`tests/test_usage_error_outcome_single_home.py`](../../tests/test_usage_error_outcome_single_home.py))
plus unit coverage
([`tests/test_contract_usage_error.py`](../../tests/test_contract_usage_error.py)).

The slice is sound and discharges its success criterion: the body-detected
exit-`2` envelope is now constructed in exactly one place, the invariant is
pinned by an `ast` guard with a positive control, and the malformed-content arms
(`RulePackError`, `LedgerError`) delegate the identical envelope rather than
re-spelling it. The docstrings on the new symbols are exemplary and the
developers' guide gained a precise paragraph distinguishing the parser-detected
from the body-detected usage fault. The findings below are tidy-ups; none is a
blocking defect, and none weakens the new home or its guard. The headline
opportunity is that the two body-fault adapters (`_scan_or_usage` and
`_set_gate_or_usage`) are now structurally identical `try`/`except
BodyUsageError-leaf`/`return usage_error_outcome(exc)` wrappers, yet each still
spells its own try-block and catches its own leaf — the catch could narrow onto
the shared `BodyUsageError` marker the task introduced precisely to unify them.

This audit reviews the merged state at `origin/main` (commit `7b3ed2f`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-separation (CQS) issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a category, a location, a description, a concrete proposed fix, and a
severity. The trail: design §3.1, §3.2 and §3.4, ADR 003 (shared interface
contract), ADR 010 (gate-drafting mutators),
[`docs/developers-guide.md`](../developers-guide.md),
[`docs/scripting-standards.md`](../scripting-standards.md), `AGENTS.md`, and the
execplan [`docs/execplans/roadmap-7-3-7.md`](../execplans/roadmap-7-3-7.md).
Navigation used `leta` and history used `sem`.

## Finding 1 — The two body-fault adapters are structurally identical and could catch the shared `BodyUsageError` marker

- Category: similarity
- Severity: medium
- Location:
  [`novel_ralph_skill/commands/_desloppify.py`](../../novel_ralph_skill/commands/_desloppify.py)
  (`_scan_or_usage`, lines 321-350) and
  [`novel_ralph_skill/commands/_gate_drafting_mutators.py`](../../novel_ralph_skill/commands/_gate_drafting_mutators.py)
  (`_set_gate_or_usage`, lines 187-205).

Both adapters now reduce to the same three-line skeleton: call the body, catch a
`BodyUsageError` leaf, and `return usage_error_outcome(exc)`. They differ only in
the inner call and the leaf subclass caught (`DesloppifyUsageError` versus
`GateDraftingUsageError`). Task 7.3.7 introduced `BodyUsageError` as the shared
marker "the body-detected exit-2 faults fan out through" (errors.py docstring),
yet each adapter still catches its own concrete leaf, so the unifying marker buys
nothing at the catch site. This is the same "thin per-module adapter re-spelling
a shared shape" smell the task closed one level down (at the envelope
construction); it survives one level up (at the try/except wrapper).

Proposed fix: catch the shared `BodyUsageError` base in both adapters rather than
the concrete leaf — `except BodyUsageError as exc: return
usage_error_outcome(exc)` — since the helper already accepts any
`EnvelopeMessagesError` and the only `BodyUsageError` either body can raise is its
own leaf. Optionally, lift the wrapper into a single contract-level higher-order
helper, e.g. `def map_body_usage(thunk: Callable[[], CommandOutcome]) ->
CommandOutcome` co-located with `usage_error_outcome`, so both sites become
`return map_body_usage(lambda: _dispatch(...))`. If the per-leaf catch is kept
deliberately (to prevent one command's adapter from swallowing another's leaf via
a shared import), record that rationale in each adapter docstring so the
similarity reads as intentional rather than as un-collapsed duplication.

## Finding 2 — `usage_error_outcome` lives in `runner.py` but is the body-fault sibling of `BodyUsageError` in `errors.py`

- Category: separation-of-concerns
- Severity: low
- Location:
  [`novel_ralph_skill/contract/runner.py`](../../novel_ralph_skill/contract/runner.py)
  (`usage_error_outcome`, lines 150-175) versus
  [`novel_ralph_skill/contract/errors.py`](../../novel_ralph_skill/contract/errors.py)
  (`BodyUsageError`, lines 49-60).

`runner.py`'s stated charter is "the shared `run` wrapper that drives a Cyclopts
app to the contract" — the parser-driving seam that owns every `sys.exit` and
envelope emission. `usage_error_outcome` is a pure, total
exception-to-`CommandOutcome` projection with no `run`/`sys.exit`/Cyclopts
coupling; it is the construction-side partner of `BodyUsageError`, which lives in
`errors.py`. Placing the helper in `runner.py` puts the body-fault projection in
the module whose own parser-fault arm the single-home guard deliberately excludes
(test docstring, Decision D3), so the two exit-`2` constructions that the task
took pains to keep conceptually separate now share a module. Every production
import already routes through the package surface
(`from novel_ralph_skill.contract import usage_error_outcome`), and every
docstring cites it as `contract.runner.usage_error_outcome`, so the physical home
is invisible to callers but visible to maintainers reasoning about the split.

Proposed fix: move `usage_error_outcome` (and, if desired, the small
`CommandOutcome` projection it depends on, or just import it) into a
construction-side module — `errors.py` beside `BodyUsageError`, or a dedicated
`contract/usage.py` — leaving `runner.py` to own only the `run`/`drive`/`_emit`
process-driving seam. The package `__init__` re-export keeps the public surface
unchanged; only the docstring `:func:` targets and the single-home test's
`contract_runner.usage_error_outcome` identity assertion need repointing. If the
co-location with `runner.py`'s own parser-fault arm is intentional (so a reader
sees both exit-`2` constructions side by side), state that rationale in the
`runner.py` module docstring, which currently does not mention
`usage_error_outcome` at all.

## Finding 3 — The runner's parser-fault arm and `usage_error_outcome` build the same envelope shape with no shared spelling

- Category: duplication
- Severity: low
- Location:
  [`novel_ralph_skill/contract/runner.py`](../../novel_ralph_skill/contract/runner.py)
  (the `CycloptsError` arm in `run`, lines 253-260, versus `usage_error_outcome`,
  lines 173-175).

The `CycloptsError` arm spells
`CommandOutcome(code=ExitCode.USAGE_ERROR, messages=[str(exc)])` inline, while
`usage_error_outcome` spells
`CommandOutcome(code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or
[str(exc)])`. These are the same envelope shape with two distinct
construction sites; the single-home guard scopes itself to the `commands` package
precisely so it does *not* flag the runner arm (test module docstring). The split
is defensible — one is parser-detected, one is body-detected — but the
`ExitCode.USAGE_ERROR` + empty-result + message shape is now duplicated across
exactly the boundary the task set out to single-home, and a future change to the
exit-`2` envelope (e.g. a non-empty `result` skeleton) must be made in two
places. The `str(exc)`-only spelling of the parser arm is also a strict subset of
the helper's `list(exc.messages) or [str(exc)]` fallback: a `CycloptsError`
carries no `.messages`, so routing it through the helper would be behaviourally
identical.

Proposed fix: have the `CycloptsError` arm delegate to the shared helper —
`_emit(context, usage_error_outcome(exc)); sys.exit(ExitCode.USAGE_ERROR)` —
since `CycloptsError` is an `Exception` with no `.messages`, the helper's
`str(exc)` fallback yields the identical `[str(exc)]`. This collapses the two
exit-`2` construction sites into one spelling without widening the guard's scope
(the guard polices the `commands` package; the runner would now *call* the home
rather than re-spell it). If the arms are kept separate by intent, add a one-line
comment at the `CycloptsError` arm cross-referencing `usage_error_outcome` so the
deliberate non-reuse is legible, mirroring the cross-reference the helper's
docstring already carries.

## Finding 4 — `usage_error_outcome`'s `list(exc.messages) or [str(exc)]` fallback has an unspecified empty-string edge

- Category: docs-gap
- Severity: low
- Location:
  [`novel_ralph_skill/contract/runner.py`](../../novel_ralph_skill/contract/runner.py)
  (`usage_error_outcome`, line 174).

The fallback `list(exc.messages) or [str(exc)]` substitutes the exception's
`str` only when `exc.messages` is empty. The docstring describes this as
"prefers the exception's recorded prose and falls back to its `str` when none was
supplied". One edge is unspecified: a fault raised with a single empty-string
message — `BodyUsageError("")` — records `messages == ("",)`, which is truthy as
a list, so the envelope carries a blank message rather than the `str(exc)`
fallback. The cross-command contract scenario asserts "the envelope carries a
non-blank message" (`cross_command_contract.feature` line 42), so a body fault
raised with a blank message would violate that contract while passing the unit
test, which only
parametrises non-blank prose and the no-message fallback
(`test_contract_usage_error.py` lines 32-34).

Proposed fix: state the intended contract in the docstring — either that callers
must supply non-blank prose (and lean on the cross-command scenario as the
enforcement), or that the helper should treat a blank/whitespace-only message as
"none supplied". If the latter is intended, change the guard to
`[m for m in exc.messages if m.strip()] or [str(exc)]` and add a
`BodyUsageError("")` parametrisation to `test_contract_usage_error.py` proving the
blank message is replaced by the `str` fallback. If blank prose is genuinely
unreachable (every raise site supplies a fixed sentence), record that invariant
in the docstring so the omission reads as deliberate.

## Finding 5 — Body-detected `desloppify` exit-2 faults lack behavioural (BDD) coverage

- Category: test-gap
- Severity: low
- Location:
  [`tests/features/cross_command_contract.feature`](../../tests/features/cross_command_contract.feature)
  (the "usage channel has the same shape" outline, lines 38-50) and
  [`tests/features/set_gate.feature`](../../tests/features/set_gate.feature)
  (the no-flag scenario, lines 23-26).

The `set-gate` no-flag body fault has a dedicated BDD scenario
(`set_gate.feature`), and the cross-command usage outline drives every command
with an *unknown option* — but that exercises the *parser*-detected
`CycloptsError` arm, not the body-detected `usage_error_outcome` path. The two
`desloppify` body faults the task reroutes — a `--chapter` outside the manifest
and a `--ledger` + `--chapter` combination — are covered only at the
command-driver unit level
([`tests/test_desloppify_command.py`](../../tests/test_desloppify_command.py)),
not behaviourally. So there is no end-to-end scenario proving a real
`desloppify` invocation with a body-detected fault emits the exit-`2` envelope
through the new single home, the way `set-gate`'s no-flag scenario does for the
gate adapter.

Proposed fix: add a scenario (to `cross_command_contract.feature` or a new
`desloppify_usage.feature`) driving `novel desloppify --chapter N` against a tree
whose manifest omits chapter `N`, asserting exit `2`, the `ok=false` skeleton,
an empty `result`, and a non-blank message — mirroring the `set-gate` no-flag
scenario. A second scenario for `--ledger PATH --chapter N` would cover the
mutual-exclusion body fault. This closes the behavioural gap so the body-detected
exit-`2` channel is exercised end-to-end for `desloppify`, not only `set-gate`.

## Finding 6 — `errors.py`'s docstring cross-references `runner.usage_error_outcome` four times, coupling the error-storage module's prose to the runner

- Category: docs-gap
- Severity: low
- Location:
  [`novel_ralph_skill/contract/errors.py`](../../novel_ralph_skill/contract/errors.py)
  (module docstring lines 13-17, class docstrings lines 30-33 and 54-59).

`errors.py` describes itself as "the single home for the
envelope-`messages`-carrying exception base" and is documented to import "nothing
from the package, so every other layer may depend on it without inviting an import
cycle". Its docstrings nonetheless reference
`novel_ralph_skill.contract.runner.usage_error_outcome` four times, naming the
runner where the body-fault envelope is built. This is sound while
`usage_error_outcome` stays in `runner.py`, but it hard-codes a sibling module's
physical location into the foundational, dependency-free error module's prose,
so the relocation proposed in Finding 2 would leave four stale `:func:` targets
to chase. The coupling is documentation-only (no import), but it makes the two
modules' docstrings move in lockstep.

Proposed fix: when Finding 2 is actioned, repoint these four references to the
new home (or to the package surface,
`novel_ralph_skill.contract.usage_error_outcome`, which is stable across a module
move). Independently of Finding 2, prefer citing the package-surface symbol in
`errors.py`'s prose rather than the runner module path, so the dependency-free
base module's documentation does not name a specific sibling module's internals.
