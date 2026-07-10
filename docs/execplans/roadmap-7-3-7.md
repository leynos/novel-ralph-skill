# Centralize the body-detected usage-error (exit-2) envelope in the contract layer

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: COMPLETE

## Purpose / big picture

Today the exit-2 ("usage error") envelope a command *body* builds when it
detects a bad invocation is re-spelled in four places, and the body-detected
usage-error exception type is copied twice. Every site repeats the same line:

```python
return CommandOutcome(
    code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or [str(exc)]
)
```

and two command modules each carry a near-verbatim
`...UsageError(EnvelopeMessagesError)` subclass whose only real difference is a
docstring trigger phrase. This is the duplication recorded in
`docs/issues/audit-2.2.4.md` Finding 1.

After this change there is a single home for both halves in the `contract`
layer:

- a `BodyUsageError(EnvelopeMessagesError)` base that each command module
  subclasses with a thin, docstring-only domain subclass, and
- one `usage_error_outcome(exc)` helper that constructs the exit-2
  `CommandOutcome` once,

and every command site that maps a body-detected fault (or a malformed-content
fault) to exit 2 calls that one helper instead of re-spelling the envelope.

Success is observable in three ways. First, a new contract unit test
(`tests/test_contract_usage_error.py`) drives `usage_error_outcome` directly and
pins the exit-2 envelope it builds — including the `list(exc.messages) or
[str(exc)]` fallback when an exception carries no `messages`. Second, a new
structural anti-drift test
(`tests/test_usage_error_outcome_single_home.py`) walks the command modules with
`ast` and fails if any of them re-spells the `CommandOutcome(code=...USAGE_ERROR,
...)` construction inline instead of routing through the shared helper. Third,
the existing desloppify, gate/drafting, ledger, and contract suites stay green —
the observable exit-2 behaviour of `set-gate`, `desloppify --chapter`,
`desloppify --ledger`, and a malformed `--pack`/`--ledger` is unchanged — so this
is a behaviour-preserving consolidation, verified by tests that already pin those
arms.

This serves the step-7.3 command-facade single-home hypothesis: the shared
exit-2 envelope seam is lifted into an explicit, neutrally-named contract home so
a refactor of one command cannot silently break the exit-2 contract of another,
and a third command module cannot copy the pattern a third time without the
structural test noticing.

## Scope: four sites, not the three the roadmap names

The roadmap text (task 7.3.7) names three exit-2 construction sites:
`_desloppify.py:256-258`, `_desloppify.py:343-345`, and
`_gate_drafting_mutators.py:204-206`. During research a **fourth** identical site
was found: `novel_ralph_skill/commands/_desloppify_ledger.py` (the malformed
device-ledger-content arm). All four build the identical
`CommandOutcome(code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or
[str(exc)])`. This plan migrates **all four** sites, because the structural
anti-drift test (WI5) would otherwise flag the un-migrated ledger site as a
regression the moment it lands, and leaving one inline copy defeats the
single-home purpose. See Decision Log D1.

The two domain subclasses to rebase onto `BodyUsageError` are
`DesloppifyUsageError` (`_desloppify.py`) and `GateDraftingUsageError`
(`_gate_drafting_mutators.py`). The `RulePackError` (in `_desloppify.py`) and
`LedgerError` (in `_desloppify_ledger.py`) arms are *malformed-content* faults,
not body-usage faults; they are **not** rebased onto `BodyUsageError` (they keep
their own typed identities and exit-3 file-fault siblings), but they *do* call
the shared `usage_error_outcome` helper because the exit-2 envelope they build is
identical. The helper therefore accepts the broad `EnvelopeMessagesError` type,
not the narrow `BodyUsageError`. See Decision Log D2.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- **No behaviour change.** Every migrated site must emit a byte-identical exit-2
  envelope (same `ok: false`, empty `result`, same `messages`) and the same exit
  code 2. The existing desloppify, gate/drafting, ledger, and cross-command
  suites are the oracle; none of their assertions may be weakened.
- **Layering direction (ADR-003, design §3.1).** The `contract` layer sits below
  `commands`, `rulepack`, and `ledger`. The new `BodyUsageError` and
  `usage_error_outcome` live in the `contract` layer and may import nothing from
  `commands` (or any layer above). The existing layering guard
  (`tests/test_contract_layering.py`) pins `contract.runner`; the new helper's
  home must respect the same rule. Do not import a `commands`/`rulepack`/`ledger`
  symbol into the helper's module.
- **`EnvelopeMessagesError` storage is unchanged.** `BodyUsageError` adds no new
  `__init__`; it inherits the freeze-on-construct `messages` tuple from
  `EnvelopeMessagesError` (`contract/errors.py`). Do not re-spell the `__init__`.
- **File-size cap (AGENTS.md).** No code file may exceed 400 lines.
  `_gate_drafting_mutators.py` is reported at 399 lines (audit-2.2.4 Finding 7),
  one under the cap. This change *removes* a class body from it (the
  `GateDraftingUsageError` definition shrinks to a one-line thin subclass), so it
  must not grow. Re-measure both `_desloppify.py` and `_gate_drafting_mutators.py`
  after editing and confirm neither breaches 400.
- **Public contract surface is additive.** `contract/__init__.py`'s `__all__`
  may gain `BodyUsageError` and `usage_error_outcome`; no existing public name
  may be removed or have its signature changed.
- **Spelling and prose.** All comments, docstrings, and commit messages use
  en-GB Oxford spelling (`-ize`/`-yse`/`-our`), per AGENTS.md and the
  `en-gb-oxendict` skill.

## Tolerances (exception triggers)

- **Scope:** if the change touches more than 8 files (net) or more than ~250
  lines of code (net) across all work items, stop and escalate.
- **Interface:** if migrating a site requires changing any *public* function
  signature (anything re-exported from `contract/__init__.py` or imported across
  module boundaries) beyond the two new additive names, stop and escalate.
- **Dependencies:** no new third-party dependency is expected. If one becomes
  necessary, stop and escalate.
- **Iterations:** if `make all` still fails after 3 fix attempts on any single
  work item, stop and escalate with the failing output captured in
  `Surprises & Discoveries`.
- **Behaviour drift:** if any existing test assertion must change to keep the
  suite green (as opposed to a *new* test being added), stop and escalate — that
  signals a behaviour change this plan forbids.
- **Ambiguity:** if a fifth exit-2 construction site is discovered that this plan
  did not enumerate, record it in `Surprises & Discoveries` and migrate it under
  the same helper rather than leaving it inline; if its shape differs from the
  canonical line, stop and escalate.

## Risks

```plaintext
- Risk: a migrated site subtly changes the emitted envelope (for example a
  different fallback when exc.messages is empty).
  Severity: high
  Likelihood: low
  Mitigation: the helper reproduces the exact `list(exc.messages) or
  [str(exc)]` expression; WI1 adds a unit test pinning both the populated and
  the empty-messages branches before any site is migrated, and the existing
  per-command exit-2 tests (test_set_gate_unit, test_desloppify_command,
  test_ledger_command) remain unchanged and must stay green.

- Risk: the structural anti-drift test (WI5) is too strict and flags a
  legitimate inline CommandOutcome (for example the exit-3 or success
  constructions, or the runner's own exit-2 arm for CycloptsError).
  Severity: medium
  Likelihood: medium
  Mitigation: scope the ast scan to the four command modules only (not
  contract.runner, whose str(CycloptsError) exit-2 arm is a parser fault, not
  a body fault, and is the legitimate single home for that path), and match
  only CommandOutcome calls whose code keyword is ExitCode.USAGE_ERROR. The
  runner's own arm stays out of scope by design (Decision Log D3).

- Risk: rebasing DesloppifyUsageError/GateDraftingUsageError onto
  BodyUsageError breaks an isinstance/except site that named the old direct
  base EnvelopeMessagesError.
  Severity: low
  Likelihood: low
  Mitigation: BodyUsageError is an EnvelopeMessagesError subclass, so every
  isinstance(x, EnvelopeMessagesError) and except EnvelopeMessagesError still
  matches; the except DesloppifyUsageError / except GateDraftingUsageError
  adapters name the leaf class, which is unchanged. Confirm with a grep for
  both class names before and after (WI2/WI3 concrete steps).

- Risk: _gate_drafting_mutators.py or _desloppify.py crosses the 400-line cap
  mid-edit.
  Severity: low
  Likelihood: low
  Mitigation: the change is net-subtractive in both modules (a multi-line
  class body shrinks to a one-line thin subclass; a multi-line CommandOutcome
  construction shrinks to a one-line helper call). Re-measure with wc -l after
  each module edit (WI2/WI3 concrete steps).
```

## Progress

- [x] WI1. Add `BodyUsageError` and `usage_error_outcome` to the contract
  layer, with a contract unit test pinning the exit-2 envelope and the
  empty-`messages` fallback. *(Done: `BodyUsageError` in
  `contract/errors.py`, `usage_error_outcome` in `contract/runner.py`, both
  re-exported and added to `__all__`; `tests/test_contract_usage_error.py`
  pins the recorded-prose path, the `str(exc)` fallback, broad-base
  acceptance, the subclass property, and package-surface importability. `make
  all` green; CodeRabbit collapsed the three helper cases into one
  parametrized test and smoothed the test docstring.)*
- [x] WI2. Rebase `DesloppifyUsageError` onto `BodyUsageError` and route both
  `_desloppify.py` exit-2 sites (the `_scan_or_usage` adapter and the
  malformed-`RulePackError` arm) through `usage_error_outcome`. *(Done:
  `DesloppifyUsageError(BodyUsageError)`, both sites call the helper, the
  now-unused `EnvelopeMessagesError` and `ExitCode` imports dropped (only the
  `BodyUsageError`/`usage_error_outcome` imports added). File shrank 390 ->
  386 lines. Added
  `test_desloppify_usage_error_is_body_usage_error`. `make all` green;
  CodeRabbit clean.)*
- [x] WI3. Rebase `GateDraftingUsageError` onto `BodyUsageError` and route the
  `_gate_drafting_mutators.py` `_set_gate_or_usage` exit-2 site through
  `usage_error_outcome`. *(Done: `GateDraftingUsageError(BodyUsageError)`,
  the adapter delegates to the helper, the `EnvelopeMessagesError` import
  dropped while `ExitCode`/`CommandOutcome` stay (the SUCCESS arms still use
  them). The module docstring's "copies the proven precedent" wording is
  re-pointed at the shared base. File 399 -> 398 lines, under the cap. Added
  `test_gate_drafting_usage_error_is_body_usage_error`. `make all` green;
  CodeRabbit clean.)*
- [x] WI4. Route the `_desloppify_ledger.py` malformed-`LedgerError` exit-2
  site through `usage_error_outcome` (the fourth site the roadmap did not
  enumerate). *(Done: the malformed-`LedgerError` arm delegates to the helper;
  `LedgerError` is deliberately not rebased (it keeps its own identity with an
  exit-3 `LedgerFileError` sibling). The `ExitCode` import is dropped and the
  now-type-only `CommandOutcome` import moved into the `TYPE_CHECKING` block
  (ruff TC001). The inline idiom is now gone from every command site (grep
  returns zero hits in `novel_ralph_skill/commands/`). `make all` green;
  CodeRabbit clean.)*
- [x] WI5. Add the structural single-home anti-drift test
  (`tests/test_usage_error_outcome_single_home.py`) that fails if any of the
  four command modules re-spells an `ExitCode.USAGE_ERROR` `CommandOutcome`
  inline. *(Done: `ast`-walk guard over every module under
  `novel_ralph_skill.commands` (recursive `rglob`, so a future nested
  subpackage is covered), excluding `contract.runner` (Decision D3). Three
  tests: the single-home assertion, a positive-control proving the guard
  fires on a synthetic inline string, and a negative control proving it
  ignores non-`USAGE_ERROR` outcomes. Red/green verified: re-inlining the
  ledger arm fails the guard naming the file+line, reverting restores green.
  `make all` green; CodeRabbit's recursive-scan note applied, its
  class-grouping note skipped to match the two existing structural-guard
  templates, which use module-level functions.)*
- [x] WI6. Update the developers' guide (and, if user-visible wording is
  affected, the users' guide) to record the single home, refresh the
  `EnvelopeMessagesError` docstring's stale enumeration, and validate the
  markdown. *(Done: developers' guide gains a paragraph naming
  `usage_error_outcome`/`BodyUsageError` as the body-detected exit-2 single
  home, distinguishing it from the runner's parser-fault arm and citing
  `tests/test_usage_error_outcome_single_home.py`. The stale
  `EnvelopeMessagesError` module and class docstrings (audit-2.2.4 Finding 5)
  are re-phrased count-agnostically (`contract`/`rulepack`/`ledger`/command
  layers) and now mention the `BodyUsageError` fan-out. The users' guide
  describes only user-visible exit-2 triggers, never the internal shape, and
  the behaviour is unchanged, so it needed no edit (read-and-confirm). The
  drift guard keys on the exit-code table and envelope field-list, neither
  touched, so it stayed green. `make all`, `make markdownlint`, `make nixie`
  all green; CodeRabbit clean.)*

## Surprises & discoveries

```plaintext
- Observation: a fourth exit-2 construction site exists beyond the three the
  roadmap names.
  Evidence: grep -rn for the messages=list(exc.messages) or [str(exc)] idiom
  over novel_ralph_skill/ returns _desloppify.py:263, _desloppify.py:353,
  _gate_drafting_mutators.py:205, and _desloppify_ledger.py:86.
  Impact: WI4 migrates the ledger site so the structural test (WI5) does not
  flag it; the helper is typed against EnvelopeMessagesError so the
  malformed-content arms (RulePackError, LedgerError) can call it too.
```

## Decision log

```plaintext
- Decision: D1 — migrate all four exit-2 sites, including the
  _desloppify_ledger.py malformed-LedgerError arm the roadmap did not list.
  Rationale: the structural anti-drift test (WI5) would flag the un-migrated
  site as a regression, and leaving one inline copy defeats the single-home
  purpose the task states. The site is byte-identical to the three named ones.
  Date/Author: 2026-06-27, planning agent.

- Decision: D2 — usage_error_outcome is typed against the broad
  EnvelopeMessagesError, not the narrower BodyUsageError.
  Rationale: two of the four sites (RulePackError, LedgerError) are
  malformed-content faults that are not body-usage faults and must keep their
  own typed identities (each has an exit-3 file-fault sibling), yet the exit-2
  envelope they build is identical to the body-usage arms. Typing the helper
  against the common base lets all four delegate. BodyUsageError remains the
  marker base only for the two genuine body-usage subclasses.
  Date/Author: 2026-06-27, planning agent.

- Decision: D3 — the structural test scopes to the four command modules and
  excludes contract.runner.
  Rationale: contract.runner builds an exit-2 CommandOutcome for a
  parser-detected CycloptsError (runner.py:230), which is the legitimate
  single home for the parser-fault path and a different concern from a
  body-detected usage fault. Folding it into the helper would couple the
  runner to the body-fault shape; it stays the home of its own arm.
  Date/Author: 2026-06-27, planning agent.

- Decision: D4 — no cuprum or external-library behaviour is load-bearing in
  this plan.
  Rationale: this is a pure in-process Python refactor. grep -rn cuprum over
  the touched modules returns nothing; the change moves a CommandOutcome
  construction and an exception base between modules in the same package. No
  subprocess execution, catalogue, allowlist, Cyclopts --help/--version path,
  pytest-timeout override, or uv run resolution semantics is relied upon, so
  the standing external-library research rule binds no claim here. The only
  library surface touched — Cyclopts raising on a bare set-gate/bad --chapter
  — is pre-existing behaviour this plan preserves unchanged and which the
  existing tests already pin; the plan asserts nothing new about it.
  Date/Author: 2026-06-27, planning agent.

- Decision: D5 — BodyUsageError lives in contract/errors.py and
  usage_error_outcome lives in contract/runner.py (split across the two
  modules), confirmed during WI1 implementation.
  Rationale: errors.py imports nothing from the package and runner.py already
  imports EnvelopeMessagesError from errors.py, so placing the helper (which
  constructs a CommandOutcome and references ExitCode) in runner.py avoids the
  import cycle an errors.py -> runner.py import would create. The plan
  anticipated this split; implementation confirmed it survives review.
  Date/Author: 2026-06-27, implementation agent.
```

## Outcomes & retrospective

Delivered against the Purpose. The exit-2 envelope now has one contract-layer
home (`usage_error_outcome` in `contract/runner.py`) and one shared body-usage
marker base (`BodyUsageError` in `contract/errors.py`), both re-exported from
`novel_ralph_skill.contract`. All four exit-2 sites delegate to the helper
(grep for the inline idiom returns zero hits across
`novel_ralph_skill/commands/`); the two genuine body-usage faults
(`DesloppifyUsageError`, `GateDraftingUsageError`) rebase onto `BodyUsageError`
as thin docstring-only leaves, while the two malformed-content faults
(`RulePackError`, `LedgerError`) keep their own typed identities yet still
delegate (Decision D2). `tests/test_contract_usage_error.py` pins the helper
(recorded-prose, `str(exc)` fallback, broad-base acceptance, subclass property,
package surface), and `tests/test_usage_error_outcome_single_home.py` forbids a
fifth inline copy with a red/green-verified `ast` guard.

No behaviour changed: every pre-existing exit-2 oracle stayed green unchanged;
only new tests were added. Both capped modules shrank (`_desloppify.py` 390 ->
386, `_gate_drafting_mutators.py` 399 -> 398), staying under the 400-line cap.
Scope held within tolerances: 8 files touched (the planned set), all net
changes subtractive in the migrated modules. CodeRabbit raised actionable
findings on WI1 (collapse the helper tests into one parametrized case; smooth
the docstring) and WI5 (recurse the command-module scan), both applied; its WI5
class-grouping note was skipped to keep the guard consistent with the two
existing structural-guard templates the plan mirrors, which use module-level
functions. No external-library or cuprum claim was load-bearing (Decision D4),
confirmed in practice — this was a pure in-process Python consolidation.

## Context and orientation

This repository is a Python package, `novel_ralph_skill`, implementing a
deterministic command harness for novel drafting. Commands emit a shared JSON
envelope and branch the harness on UNIX exit codes (design §3.1, §3.2;
`docs/adr-003-shared-interface-contract.md`). Exit code 2 means "usage error:
the invocation is wrong" (design §3.2 Table; `contract/exit_codes.py`,
`ExitCode.USAGE_ERROR = 2`).

The relevant layers, by full path:

- `novel_ralph_skill/contract/` — the shared interface contract. Below every
  other layer; imports nothing from `commands`/`rulepack`/`ledger`.
  - `contract/errors.py` defines `EnvelopeMessagesError(Exception)`: a base that
    records `self.messages: tuple[str, ...]` once at construction. Every domain
    error that needs to carry human prose for the envelope's `messages` array
    subclasses it.
  - `contract/runner.py` defines `CommandOutcome` (a frozen dataclass with
    `code: ExitCode`, `result`, `messages`), `StateInputError` (the exit-3
    subclass of `EnvelopeMessagesError`), and the `run`/`drive` seams. The runner
    itself builds one exit-2 `CommandOutcome` for a *parser*-detected
    `CycloptsError` (`runner.py:230`) — out of scope for this plan (Decision D3).
  - `contract/exit_codes.py` defines `ExitCode` (an `IntEnum`).
  - `contract/__init__.py` re-exports the public contract surface and pins it in
    `__all__`.
- `novel_ralph_skill/commands/_desloppify.py` — the `desloppify` body. Defines
  `DesloppifyUsageError(EnvelopeMessagesError)` (a body-detected usage fault: a
  `--chapter` outside the manifest, or `--ledger` + `--chapter`) and the
  `_scan_or_usage` adapter that catches it and returns the exit-2 outcome
  (`_desloppify.py:353`). It also catches a `RulePackError` (malformed pack
  *content*) and returns the *same-shaped* exit-2 outcome (`_desloppify.py:263`).
- `novel_ralph_skill/commands/_desloppify_ledger.py` — the `desloppify --ledger`
  body. Catches `LedgerError` (malformed ledger *content*) and returns the same
  exit-2 outcome (`_desloppify_ledger.py:86`). `LedgerError` is defined in
  `novel_ralph_skill/ledger/errors.py`.
- `novel_ralph_skill/commands/_gate_drafting_mutators.py` — the `set-gate` and
  sibling mutators. Defines `GateDraftingUsageError(EnvelopeMessagesError)` (a
  no-flag `set-gate`, which parses cleanly to `{}`) and the `_set_gate_or_usage`
  adapter that returns the exit-2 outcome (`_gate_drafting_mutators.py:205`).

The canonical exit-2 line, identical at all four sites:

```python
return CommandOutcome(
    code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or [str(exc)]
)
```

The `list(exc.messages) or [str(exc)]` idiom: if the exception was constructed
with prose (`messages` is a non-empty tuple), use it; otherwise fall back to the
exception's `str()`. The helper must reproduce this exactly.

Precedent for the structural pattern this plan follows: roadmap task 7.3.3
(`docs/execplans/roadmap-7-3-3.md`) lifted a shared draft-read state-error
wrapper into a neutral home and pinned the single-home property with an `ast`
structural test (its WI5) plus a developers'-guide note (its WI6). Roadmap task
7.3.5 added `tests/test_entry_point_single_home.py` and
`tests/test_contract_layering.py`, both `ast`-walk structural guards — read these
two files as templates for WI5. The existing exit-2 behavioural oracles are
`tests/test_set_gate_unit.py` (`test_set_gate_no_flag_is_usage_error`),
`tests/test_desloppify_command.py` (the malformed-pack, bad-`--chapter`, and
`--ledger`+`--chapter` exit-2 tests), and `tests/test_ledger_command.py` (the
malformed-ledger-content exit-2 test).

## Plan of work

Work proceeds in dependency order. WI1 establishes the shared home and its unit
test first (red before green: the unit test is written against the new helper, so
it fails to import until the helper exists, then passes). WI2–WI4 migrate the
four sites, each a self-contained, gate-passable commit that leaves the suite
green because the migrated behaviour is identical. WI5 adds the structural guard
once all four sites route through the helper (it would fail if added before WI4).
WI6 documents the consolidation and validates the markdown.

Each work item runs `make all` before its commit (AGENTS.md quality gates: build,
check-fmt, lint, typecheck, test). WI6 additionally runs `make markdownlint` and
`make nixie`.

### Stage B/C — the shared home (WI1)

#### WI1 — Add `BodyUsageError` and `usage_error_outcome` to the contract layer

Implements: design §3.2 (exit-2 usage-error channel); ADR-003 (shared interface
contract, single output shape); audit-2.2.4 Finding 1 (proposed fix). Roadmap
task 7.3.7.

Docs to read first: `docs/novel-ralph-harness-design.md` §3.1 and §3.2;
`docs/adr-003-shared-interface-contract.md`; `docs/issues/audit-2.2.4.md` Finding
1 and Finding 5; `docs/scripting-standards.md` (en-GB prose, docstring
conventions); `AGENTS.md` (quality gates, docstring-coverage gate, 400-line cap).

Skills to load: `python-router` (route to the smaller Python skills it points
to); `python-errors-and-logging` (exception-base design, narrow subclassing);
`python-types-and-apis` (the helper's public signature); `en-gb-oxendict` (prose
spelling). For the test-design choice, load `python-verification` to confirm an
example-based unit test is the right adversary here (it is — the helper is a pure
total function over a small, enumerable input space: a populated-`messages`
exception and an empty-`messages` exception; neither Hypothesis nor CrossHair
buys coverage a two-case example test does not, and the plan records that
decision rather than reaching for property tools reflexively).

Where the new code lives: add both symbols to `contract/errors.py` (the natural
home: it already owns `EnvelopeMessagesError`, the base they build on, and it
imports nothing from the package). `usage_error_outcome` returns a
`CommandOutcome`, which lives in `contract/runner.py`; importing `CommandOutcome`
and `ExitCode` *into* `errors.py` would make `errors.py` depend on `runner.py`.
Check the current dependency direction first: `runner.py` imports
`EnvelopeMessagesError` *from* `errors.py` (`runner.py:42`), so `errors.py` must
not import from `runner.py` or it creates an import cycle. Therefore:

- `BodyUsageError(EnvelopeMessagesError)` goes in `contract/errors.py` (no new
  dependency; it is a pure subclass).
- `usage_error_outcome(exc)` goes in `contract/runner.py` (alongside
  `CommandOutcome`, which it constructs, and `ExitCode`, which it references —
  both already in scope there). It imports the `EnvelopeMessagesError` type it
  accepts from `errors.py`, which `runner.py` already does.

This split respects the existing import direction and avoids a cycle. Record it
in the Decision Log if it survives review (Decision D5, to be added during
implementation).

`BodyUsageError` body, in `contract/errors.py`, immediately after
`EnvelopeMessagesError`:

```python
class BodyUsageError(EnvelopeMessagesError):
    """A body-detected usage fault routed to exit ``2`` (design §3.2).

    The shared marker base for a usage fault a command *body* detects after the
    Cyclopts parser has accepted the invocation — the parser cannot catch it, so
    it never reaches the runner's ``CycloptsError`` arm. Each command module
    keeps a thin domain subclass naming its own trigger (a no-flag ``set-gate``,
    a ``--chapter`` outside the manifest), but the exit-``2`` envelope every such
    fault produces is built once by
    :func:`~novel_ralph_skill.contract.runner.usage_error_outcome`. The optional
    ``messages`` payload is recorded once by :class:`EnvelopeMessagesError`.
    """
```

`usage_error_outcome` body, in `contract/runner.py`, near `CommandOutcome`:

```python
def usage_error_outcome(exc: EnvelopeMessagesError) -> CommandOutcome:
    """Build the exit-``2`` usage-error outcome for a body-detected fault.

    The single home for the exit-``2`` envelope a command body returns when it
    detects a bad invocation the Cyclopts parser accepted (design §3.2; ADR-003).
    The ``messages`` payload prefers the exception's recorded prose and falls back
    to its ``str`` when none was supplied, so every command site emits the same
    shape rather than re-spelling it (audit-2.2.4 Finding 1).

    Parameters
    ----------
    exc : EnvelopeMessagesError
        The raised body fault. A :class:`BodyUsageError` subclass for a genuine
        usage fault, or a malformed-content error (``RulePackError``,
        ``LedgerError``) whose exit-``2`` envelope is identical in shape.

    Returns
    -------
    CommandOutcome
        An ``ExitCode.USAGE_ERROR`` outcome carrying ``exc``'s prose (or its
        ``str`` fallback) and an empty ``result``.
    """
    return CommandOutcome(
        code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or [str(exc)]
    )
```

Export both from `contract/__init__.py`: add `BodyUsageError` to the
`from ...contract.errors import` group and `usage_error_outcome` to the
`from ...contract.runner import` group, add both to `__all__` (keep `__all__`
sorted as the file already is), and add both to the module-docstring's
"public surface re-exported here" enumeration.

Tests to add (this work item, red-before-green): create
`tests/test_contract_usage_error.py` with:

- `test_usage_error_outcome_uses_recorded_messages` — construct a
  `BodyUsageError("a", "b")`, call `usage_error_outcome`, assert the returned
  outcome has `code == ExitCode.USAGE_ERROR`, `result == {}`, and
  `tuple(outcome.messages) == ("a", "b")`.
- `test_usage_error_outcome_falls_back_to_str` — construct a `BodyUsageError()`
  with no messages, assert `tuple(outcome.messages) == (str(exc),)` and the same
  exit code / empty result. (Pins the `or [str(exc)]` branch.)
- `test_usage_error_outcome_accepts_any_envelope_error` — pass a plain
  `EnvelopeMessagesError("x")` (the broad accepted type) and assert it produces
  the exit-2 outcome, documenting that malformed-content arms may call it too
  (Decision D2).
- `test_body_usage_error_subclasses_envelope_base` — assert
  `issubclass(BodyUsageError, EnvelopeMessagesError)` and that a
  `BodyUsageError("m")` round-trips `messages == ("m",)`.
- `test_symbols_importable_from_package_surface` — assert
  `contract.BodyUsageError` and `contract.usage_error_outcome` resolve and are
  the same objects as the module-level definitions (mirrors the
  `test_contract_errors.py::test_importable_from_both_paths` precedent).

These are example-based pytest unit tests in the top-level `tests/` tree
(AGENTS.md: no unit tests inside package dirs). No snapshot is added here — the
contract envelope already has snapshot coverage in
`tests/test_contract_envelope_snapshots.py` and the per-command exit-2 envelopes
are snapshotted by their own suites; a fresh helper-level snapshot would be
snapshot-only coverage for logic asserted directly (AGENTS.md snapshot rule), so
the plan uses semantic assertions instead.

Validation: `make all` green; the new file's five tests pass (and fail to import
before the helper exists — the red state). Confirm the docstring-coverage gate
(`interrogate`) still passes, since two new public symbols were added with full
docstrings.

### Stage C — migrate the four sites (WI2, WI3, WI4)

#### WI2 — Rebase `DesloppifyUsageError` and route both `_desloppify.py` sites

Implements: audit-2.2.4 Finding 1; design §3.2; roadmap task 7.3.7.

Docs to read first: `docs/issues/audit-2.2.4.md` Finding 1; the `_desloppify.py`
module docstring (it openly states it "copies the proven
`_desloppify.DesloppifyUsageError` + `_scan_or_usage` precedent" — that wording
is now superseded and the comment that names the copy should be retired or
re-pointed at the shared helper).

Skills to load: `python-router` → `python-errors-and-logging`; `leta` for
finding every reference to `DesloppifyUsageError` before editing its base.

Edits, in `novel_ralph_skill/commands/_desloppify.py`:

1. Change the class declaration from
   `class DesloppifyUsageError(EnvelopeMessagesError):` to
   `class DesloppifyUsageError(BodyUsageError):`. Trim the docstring to the
   domain-specific trigger (a `--chapter` outside the manifest, or
   `--ledger` + `--chapter`) and point the "shape" sentence at `BodyUsageError`
   rather than re-describing the exit-2 mapping (which now lives in the helper).
2. Update the import line: `_desloppify.py:52` imports
   `EnvelopeMessagesError` from `contract.errors`. Replace it with imports of
   `BodyUsageError` (from `contract` or `contract.errors`) and
   `usage_error_outcome` (from `contract` or `contract.runner`). Match the
   module's existing import style (the file imports `CommandOutcome`,
   `ExitCode`, etc. from `contract`; prefer the package surface
   `from novel_ralph_skill.contract import ...` for the two new names so the
   import set stays uniform). If `EnvelopeMessagesError` is no longer referenced
   anywhere in the file after the rebase, drop its import (run `leta refs` /
   `grep` to confirm).
3. At the `_scan_or_usage` adapter (`_desloppify.py:353`), replace the inline
   `return CommandOutcome(code=ExitCode.USAGE_ERROR, messages=list(exc.messages)
   or [str(exc)])` with `return usage_error_outcome(exc)`.
4. At the malformed-`RulePackError` arm (`_desloppify.py:263`), replace the same
   inline construction with `return usage_error_outcome(exc)`. (`RulePackError`
   is an `EnvelopeMessagesError`, so the broad-typed helper accepts it — Decision
   D2.)

Tests to add/update: no new behavioural test is required because the migrated
behaviour is identical and `tests/test_desloppify_command.py` already pins all
three desloppify exit-2 arms (malformed pack, bad `--chapter`, `--ledger` +
`--chapter`). Add one *typing/identity* assertion to the desloppify command
suite (or to `tests/test_contract_usage_error.py` if it reads more naturally
as a contract test): `test_desloppify_usage_error_is_body_usage_error`
asserting `issubclass(DesloppifyUsageError, BodyUsageError)`, so the rebase is
pinned and a future revert to the bare `EnvelopeMessagesError` base is caught.
Per AGENTS.md this is the "fully validated by relevant tests" requirement met
by the unchanged behavioural oracle plus the new rebase assertion.

Concrete checks before commit: `grep -rn "DesloppifyUsageError"
novel_ralph_skill/ tests/` to confirm every `except`/`isinstance` site still
names the leaf class (unchanged); `wc -l novel_ralph_skill/commands/_desloppify.py`
to confirm it did not grow past 400 (it should shrink).

Validation: `make all` green; `tests/test_desloppify_command.py` and
`tests/test_desloppify_snapshots.py` pass unchanged.

#### WI3 — Rebase `GateDraftingUsageError` and route the `set-gate` site

Implements: audit-2.2.4 Finding 1 and Finding 7 (the 400-line headroom note);
design §3.2; roadmap task 7.3.7.

Docs to read first: `docs/issues/audit-2.2.4.md` Finding 1 and Finding 7;
`docs/adr-010-gate-drafting-mutators.md` (the gate/drafting mutator family, for
context on the no-flag `set-gate` usage arm).

Skills to load: `python-router` → `python-errors-and-logging`; `leta` for the
`GateDraftingUsageError` reference scan.

Edits, in `novel_ralph_skill/commands/_gate_drafting_mutators.py`:

1. Change `class GateDraftingUsageError(EnvelopeMessagesError):` to
   `class GateDraftingUsageError(BodyUsageError):`. Trim its docstring to the
   no-flag `set-gate` trigger; drop the "copies the
   `_desloppify.DesloppifyUsageError` precedent" sentence (the shared base now
   *is* the precedent) and the re-description of the exit-2 mapping.
2. Update the import at `_gate_drafting_mutators.py:54` the same way as WI2:
   import `BodyUsageError` and `usage_error_outcome`, drop the now-unused
   `EnvelopeMessagesError` import if no other reference remains.
3. At the `_set_gate_or_usage` adapter (`_gate_drafting_mutators.py:205`),
   replace the inline `CommandOutcome(code=ExitCode.USAGE_ERROR, ...)` with
   `return usage_error_outcome(exc)`.

Tests to add/update: the behavioural oracle
`tests/test_set_gate_unit.py::test_set_gate_no_flag_is_usage_error` is unchanged
and must stay green. Add `test_gate_drafting_usage_error_is_body_usage_error`
(in the gate/drafting unit suite or `test_contract_usage_error.py`) asserting
`issubclass(GateDraftingUsageError, BodyUsageError)`.

Concrete checks before commit: `grep -rn "GateDraftingUsageError"
novel_ralph_skill/ tests/`; `wc -l
novel_ralph_skill/commands/_gate_drafting_mutators.py` — confirm it is **at or
below** its prior 399 and not over 400 (Constraint; the net change is
subtractive).

Validation: `make all` green; `tests/test_set_gate_unit.py`,
`tests/test_set_gate_properties.py`, and `tests/test_gate_drafting_mutators_e2e.py`
pass unchanged.

#### WI4 — Route the `_desloppify_ledger.py` malformed-ledger site

Implements: audit-2.2.4 Finding 1 (extended to the fourth site, Decision D1);
design §3.2; roadmap task 7.3.7.

Docs to read first: `docs/issues/audit-2.2.4.md` Finding 1;
`novel_ralph_skill/ledger/errors.py` docstring (it documents `LedgerError` as the
malformed-*content* exit-2 arm, distinct from the exit-3 `LedgerFileError`).

Skills to load: `python-router` → `python-errors-and-logging`.

Edits, in `novel_ralph_skill/commands/_desloppify_ledger.py`:

1. Import `usage_error_outcome` (from `contract`, matching the module's existing
   `from novel_ralph_skill.contract import CommandOutcome, ExitCode` style).
2. At the malformed-`LedgerError` arm (`_desloppify_ledger.py:86`), replace the
   inline `return CommandOutcome(code=ExitCode.USAGE_ERROR, messages=list(...)
   or [str(exc)])` with `return usage_error_outcome(exc)`. (`LedgerError` is an
   `EnvelopeMessagesError`, accepted by the broad helper — Decision D2.) Do
   **not** rebase `LedgerError` onto `BodyUsageError`: it is a malformed-content
   fault with an exit-3 file sibling (`LedgerFileError`) and must keep its own
   typed identity.
3. If `CommandOutcome`/`ExitCode` are no longer referenced elsewhere in the file
   after the swap, leave their imports if still used (the success/finding outcome
   path uses them via `ledger_report_outcome`; confirm with `grep` and keep only
   what is referenced to satisfy the unused-import lint).

Tests to add/update: `tests/test_ledger_command.py`'s malformed-ledger-content
exit-2 test (and `tests/test_desloppify_command.py::...ledger...malformed...`)
are the unchanged oracle and must stay green. No new rebase assertion is needed
because `LedgerError` is deliberately *not* rebased; the structural test in WI5
covers the helper-delegation property for this site.

Concrete checks before commit: `grep -rn "messages=list(exc.messages) or
\[str(exc)\]" novel_ralph_skill/` — after WI2–WI4 this must return **zero hits**
in `novel_ralph_skill/commands/` (the inline idiom is gone from every command
site). `wc -l novel_ralph_skill/commands/_desloppify_ledger.py`.

Validation: `make all` green; `tests/test_ledger_command.py`,
`tests/test_ledger_snapshots.py`, and the ledger desloppify arms pass unchanged.

### Stage D — harden and document (WI5, WI6)

#### WI5 — Structural single-home anti-drift test

Implements: the step-7.3 single-home hypothesis; audit-2.2.4 Finding 1 ("the
exit-2 envelope construction lives in exactly one place"); roadmap task 7.3.7
success criterion ("the exit-2 envelope construction lives in exactly one
place").

Docs to read first: `tests/test_entry_point_single_home.py` and
`tests/test_contract_layering.py` (the two `ast`-walk structural-guard
templates); `docs/execplans/roadmap-7-3-3.md` WI5 (the precedent
single-home structural test for a consolidated wrapper); AGENTS.md (test
placement, docstring coverage on the new test module).

Skills to load: `python-router` → `python-testing` (the `ast`-walk structural
test technique, fixture scope); `leta` for confirming the module list to scan.

Where the test lives: `tests/test_usage_error_outcome_single_home.py`.

What it asserts: statically parse each of the four command modules
(`_desloppify.py`, `_desloppify_ledger.py`, `_gate_drafting_mutators.py`, and —
for completeness, so a *new* command module cannot reintroduce the idiom
silently — every module under `novel_ralph_skill/commands/` that constructs a
`CommandOutcome`). Walk the `ast`; for every `ast.Call` whose callee resolves to
`CommandOutcome` and whose `code` keyword argument is the attribute
`ExitCode.USAGE_ERROR`, fail with a message naming the file and line. The
positive control: assert at least one module (or a fixture string) demonstrates
the guard *would* fire on an inline construction, so the test cannot silently
pass by scanning nothing (mirror the "fails before, passes after" discipline —
this test fails on the pre-WI2 tree and passes on the post-WI4 tree).

Scope exclusions (Decision D3): the scan covers `novel_ralph_skill/commands/`
only. It does **not** scan `contract/runner.py`, whose `CycloptsError` exit-2 arm
(`runner.py:230`) is the legitimate single home for the *parser*-fault path and
is a different concern from a body-detected fault. The test docstring must state
this exclusion and why, so a future reader does not "fix" it by widening scope.

Implementation notes mirroring the existing guards:

- Resolve each module's source via `importlib.util.find_spec(...).origin` and
  read it as text, parsing with `ast.parse` — do **not** import-and-execute the
  command modules at collection time (the `test_contract_layering.py` precedent;
  avoids pulling lazy leaf modules at collection).
- Match the `CommandOutcome` callee as either an `ast.Name` (`CommandOutcome(...)`)
  or an `ast.Attribute` tail (`module.CommandOutcome(...)`), reusing the
  `_callee_name` helper shape from `test_entry_point_single_home.py`.
- Match the `code=ExitCode.USAGE_ERROR` keyword by walking `call.keywords` for a
  keyword named `code` whose value is an `ast.Attribute` with `attr ==
  "USAGE_ERROR"`.

Tests this work item adds: the file above (one or two test functions: the
single-home assertion over the command modules, and the positive-control
assertion that the guard fires on a synthetic inline-construction string).

Validation: `make all` green; the new guard passes on the post-WI4 tree. Sanity:
temporarily re-inline one site, confirm the guard fails, then revert (record the
red/green evidence in `Artifacts and notes`).

#### WI6 — Document the single home and refresh the stale base docstring

Implements: AGENTS.md "Documentation maintenance" (update `docs/` to reflect the
change); audit-2.2.4 Finding 5 (the stale `EnvelopeMessagesError` enumeration);
design §3.2; roadmap task 7.3.7.

Docs to read first: `docs/developers-guide.md` (the contract-error / exit-2 arm
sections around the "single home" language, lines ~146–188);
`docs/documentation-style-guide.md`; `AGENTS.md` (markdown lint and nixie gates,
en-GB Oxford spelling).

Skills to load: `en-gb-oxendict` (prose spelling); `python-router` →
`python-errors-and-logging` only if the docstring rewording needs a sanity check.

Edits:

1. `docs/developers-guide.md`: add a short paragraph (in the contract / error
   section that already discusses the exit-2 usage arm) naming
   `usage_error_outcome` and `BodyUsageError` as the single home for the
   body-detected exit-2 envelope, and noting that `desloppify`, `set-gate`, and
   the ledger arm delegate to it while keeping thin domain subclasses. Reference
   `tests/test_usage_error_outcome_single_home.py` as the guard, matching how the
   guide already cites single-home guards elsewhere.
2. `novel_ralph_skill/contract/errors.py`: fix the stale docstring (audit-2.2.4
   Finding 5). The base's class docstring still claims "the three domain
   exceptions" and enumerates only `StateInputError`, `RulePackError`,
   `RulePackFileError`. Replace the brittle hand-maintained enumeration with the
   count-agnostic phrasing the audit proposes (e.g. "the domain error types
   across the `contract`, `rulepack`, `ledger`, and command layers subclass it"),
   and mention that the body-usage faults now fan out through the
   `BodyUsageError` marker. (This is a docstring edit in a code file, so it is
   covered by `make all`'s `interrogate` gate, not only the markdown gates.)
3. `docs/users-guide.md`: review for any user-visible wording change. None is
   expected — exit-2 behaviour and messages are unchanged — so this is a
   read-and-confirm step; only edit if a user-facing description of the exit-2
   behaviour names the internal shape (it should not).

Tests this work item adds/updates: there is a developers'-guide drift guard
(`tests/test_developers_guide_contract_drift_guard.py`). If the new paragraph
introduces a claim that guard checks (or the guard asserts a fixed set of
documented single-homes), update the guard's expectation accordingly and keep it
green; if the guard does not key on this section, no test change is needed.
Confirm by reading the guard before editing the guide.

Validation: `make all` green (covers the `errors.py` docstring change and the
drift guard); `make markdownlint` and `make nixie` green (markdown changes).

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-3-7`. Confirm the
branch first:

```bash
git branch --show-current   # expect: roadmap-7-3-7
```

1. WI1: edit `novel_ralph_skill/contract/errors.py` (add `BodyUsageError`) and
   `novel_ralph_skill/contract/runner.py` (add `usage_error_outcome`); update
   `novel_ralph_skill/contract/__init__.py` (imports, `__all__`, docstring);
   create `tests/test_contract_usage_error.py`. Run `make all`. Commit.
2. WI2: edit `novel_ralph_skill/commands/_desloppify.py` (rebase subclass, swap
   both sites, fix imports); add the rebase assertion test. `grep -rn
   "DesloppifyUsageError"`; `wc -l` the file. Run `make all`. Commit.
3. WI3: edit `novel_ralph_skill/commands/_gate_drafting_mutators.py` (rebase
   subclass, swap the site, fix imports); add the rebase assertion test. `grep`
   and `wc -l`. Run `make all`. Commit.
4. WI4: edit `novel_ralph_skill/commands/_desloppify_ledger.py` (swap the site,
   add import). Confirm `grep -rn "messages=list(exc.messages) or \[str(exc)\]"
   novel_ralph_skill/commands/` returns nothing. Run `make all`. Commit.
5. WI5: create `tests/test_usage_error_outcome_single_home.py`. Verify red/green
   by temporarily re-inlining one site (then revert). Run `make all`. Commit.
6. WI6: edit `docs/developers-guide.md`, `novel_ralph_skill/contract/errors.py`
   (docstring), review `docs/users-guide.md`; update the developers'-guide drift
   guard if it keys on the edited section. Run `make all`, then `make
   markdownlint` and `make nixie`. Commit.

Expected `make all` tail on each commit:

```plaintext
... passed ...
```

(exact counts grow as the new tests land; no test may be skipped or xfail-ed).

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes with the new `tests/test_contract_usage_error.py`
  (five-plus tests) and `tests/test_usage_error_outcome_single_home.py` (the
  structural guard) green, and every pre-existing exit-2 oracle
  (`test_set_gate_unit`, `test_desloppify_command`, `test_ledger_command`,
  `test_gate_drafting_mutators_e2e`, the cross-command contract suites)
  unchanged and green. The structural guard fails on the pre-WI2 tree (any inline
  site) and passes on the post-WI4 tree.
- Lint/typecheck: `make lint` and `make typecheck` pass; `interrogate` shows 100%
  docstring coverage including the two new public symbols and the new test
  modules. No unused-import warning from the dropped `EnvelopeMessagesError`
  imports.
- File size: `wc -l` confirms no command file exceeds 400 lines; both
  `_desloppify.py` and `_gate_drafting_mutators.py` are unchanged-or-shrunk.
- Behaviour: a no-flag `set-gate`, a `desloppify --chapter` outside the manifest,
  a `desloppify --ledger --chapter` combination, a malformed `--pack`, and a
  malformed `--ledger` each still exit 2 with the same envelope (verified by the
  unchanged oracles).
- Markdown: `make markdownlint` and `make nixie` pass for the doc changes.

Quality method (how we check): `make all` on each commit; `make markdownlint` and
`make nixie` on the WI6 commit. The single-home guard plus the unchanged
behavioural oracles together prove the consolidation is both complete (one home)
and behaviour-preserving.

## Idempotence and recovery

Every work item is a small, self-contained, separately committed edit. Re-running
`make all` is safe and side-effect-free. If a migrated site is found to differ in
behaviour, `git revert` the offending commit and re-do it; the unchanged oracles
will catch the difference before the commit lands (they run in `make all`). The
red/green check in WI5 is reversible (re-inline then revert) and leaves the tree
clean.

## Artefacts and notes

After WI4, `grep -rn "messages=list(exc.messages) or \[str(exc)\]"
novel_ralph_skill/commands/` returns **zero hits** — the inline exit-2 idiom is
gone from every command site. The two capped modules shrank: `_desloppify.py`
390 -> 386 lines, `_gate_drafting_mutators.py` 399 -> 398 lines (both under the
400-line cap). `_desloppify_ledger.py` shrank 97 -> 96 lines.

WI5 red/green transcript: with all four sites delegating, the structural guard
passes on the post-WI4 tree; temporarily re-inlining one site
(`_desloppify_ledger.py` malformed arm) makes
`test_command_modules_route_exit_2_through_the_shared_helper` fail naming the
re-inlined file and line, and reverting restores green. The positive-control
test proves the guard fires on a synthetic inline-construction source string.

## Interfaces and dependencies

At the end of this work the following must exist:

In `novel_ralph_skill/contract/errors.py`:

```python
class BodyUsageError(EnvelopeMessagesError):
    """A body-detected usage fault routed to exit ``2`` (design §3.2)."""
```

In `novel_ralph_skill/contract/runner.py`:

```python
def usage_error_outcome(exc: EnvelopeMessagesError) -> CommandOutcome:
    """Build the exit-``2`` usage-error outcome for a body-detected fault."""
```

Both re-exported from `novel_ralph_skill.contract` (added to `__all__`).

`novel_ralph_skill.commands._desloppify.DesloppifyUsageError` and
`novel_ralph_skill.commands._gate_drafting_mutators.GateDraftingUsageError` each
subclass `BodyUsageError`. All four command exit-2 sites call
`usage_error_outcome`. No new third-party dependency. No public signature changes
beyond the two additive names.

## Addenda

Lightweight, post-completion corrections folded onto this task. Each is a small,
surgical fix run as a no-plan, no-review pass; none changes the task's outcome.

- [ ] A1 (from audit:7.3.7 Finding 5; low). Add behavioural coverage for
  `desloppify` body-detected exit-2 faults. The body-detected exit-2 path through
  `usage_error_outcome` is exercised end-to-end only for `set-gate`'s no-flag
  fault; `desloppify`'s bad-chapter and `--ledger`+`--chapter` body faults are
  covered only at the unit-driver level. Add a scenario driving a real
  `desloppify` invocation with a manifest-absent `--chapter` (and one for the
  `--ledger`+`--chapter` combination) so the 7.3.7 single home is proven
  end-to-end for `desloppify` too. Behaviour-preserving test addition. Scope: the
  desloppify behavioural suite. Mirrors roadmap sub-task 7.3.7.1.
