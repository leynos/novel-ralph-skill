# Consolidate the rule-pack and device-ledger error hierarchies behind one shared `loaderkit.errors` factory

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DRAFT

## Purpose / big picture

The rule-pack loader (`novel_ralph_skill/rulepack/errors.py`) and the
device-ledger loader (`novel_ralph_skill/ledger/errors.py`) each carry a
structurally identical two-class failure hierarchy: a content error
(`RulePackError` / `LedgerError`, exit 2) and a file error (`RulePackFileError`
/ `LedgerFileError`, exit 3), both subclassing
`novel_ralph_skill.contract.errors.EnvelopeMessagesError`. The two copies
differ only in (a) the id-attribute keyword name (`rule_id` versus `device_id`),
(b) the human-facing nouns in their docstrings, and (c) the class names. This is
the same near-copy that roadmap task 7.2.2 retired for the *coercion* and *scan*
bodies by lifting them into `loaderkit`, but task 7.2.2 deliberately scoped the
typed error channels out (it kept "each package's typed error type" unchanged;
see `docs/execplans/roadmap-7-2-2.md`, Decision D-FACTORY rationale).

After this change a maintainer adding a third loader family (the per-novel packs
foreshadowed in design §8.1, and the seam roadmap 8.1.9 already assumes exists)
*binds* one shared error-hierarchy factory rather than hand-copying a third pair
of near-identical classes. Success is observable three ways: (1) the two
`errors.py` modules no longer each spell out their own
`class …Error(EnvelopeMessagesError)` body with a bespoke `__init__` — they
subclass a single shared `loaderkit.errors` base; (2) every existing test
that imports `RulePackError`, `RulePackFileError`, `LedgerError`,
`LedgerFileError`, constructs them with `rule_id=`/`device_id=`, catches them by
name, or reads `.rule_id`/`.device_id`/`.messages` still passes unchanged; and
(3) a new `tests/test_loaderkit_errors.py` pins the factory so a third family
inherits the primitive instead of cloning a third copy.

The public surface — class names, the `rule_id`/`device_id` attribute names,
each typed error channel, the exit-code mapping the command layer performs, and
every operator-facing message string — is unchanged. This is a pure internal
refactor: no behaviour changes, no snapshot regeneration.

## Constraints

Hard invariants that must hold throughout. Violation requires escalation, not a
workaround.

- **No behaviour change, no message change, no snapshot regeneration.** The
  loaders must raise the same four error *types*, carrying the same `messages`
  tuples and the same `rule_id`/`device_id` values, so every command-layer
  `except RulePackError` / `except LedgerFileError` arm and every syrupy
  snapshot under `tests/__snapshots__/` and
  `tests/cross_command_contract/__snapshots__/` stays byte-identical. Do **not**
  run `--snapshot-update`.
- **Class identity and names are public and must be preserved.** The command
  layer catches these by name (`novel_ralph_skill/commands/_desloppify.py:258`,
  `:263`; `novel_ralph_skill/commands/_desloppify_ledger.py:83`, `:88`),
  `tests/test_contract_errors.py` asserts `issubclass(RulePackError,
  EnvelopeMessagesError)`, and the package `__init__` modules re-export them in
  `__all__`. `RulePackError.__name__` must stay `"RulePackError"` etc., each
  must remain importable as `novel_ralph_skill.rulepack.errors.RulePackError`
  (and from `novel_ralph_skill.rulepack`), and each must subclass
  `EnvelopeMessagesError`. `RulePackError` and `LedgerError` must remain
  *distinct* classes (not aliases) so a `desloppify` command catching one does
  not accidentally catch the other.
- **The id keyword name is public and per-package.** Call sites construct
  `RulePackError(msg, rule_id=rule_id)`
  (`novel_ralph_skill/rulepack/parse.py:114,151,160,191,200,259`) and
  `LedgerError(msg, device_id=device_id)`
  (`novel_ralph_skill/ledger/_fields.py` ×6,
  `novel_ralph_skill/ledger/parse.py:114,179`). The `_coerce.py` bindings build
  the `CoercionErrors` bundle with
  `content_error=lambda msg, rule_id: RulePackError(msg, rule_id=rule_id)` and
  the device equivalent. The factory product must accept the id by *that exact
  keyword name* and store it as an attribute of *that exact name*, defaulting to
  `None`. Tests read `excinfo.value.rule_id` / `.device_id`
  (`tests/test_rulepack_loader.py`, `tests/test_ledger_*`).
- **The file-error type is a bare `*messages` constructor passed as a
  callable.** `RulePackFileError` and `LedgerFileError` are handed to
  `loaderkit.load.load_toml` as the `file_error=` argument
  (`novel_ralph_skill/rulepack/parse.py:303`,
  `novel_ralph_skill/ledger/parse.py:225`), where they are called as
  `file_error(msg)`. They must remain `EnvelopeMessagesError` subclasses with no
  extra constructor arguments, so the `cabc.Callable[[str],
  EnvelopeMessagesError]` contract in `load_toml` holds.
- **`loaderkit` stays a neutral leaf.** `novel_ralph_skill/loaderkit/errors.py`
  must import nothing from `rulepack` or `ledger` — at runtime or under
  `TYPE_CHECKING` — exactly as the other `loaderkit` modules do (design §6,
  §6.3; `docs/adr-003-shared-interface-contract.md`). It may depend only on
  `novel_ralph_skill.contract.errors` and the standard library. The
  parametrised `loaderkit` import-direction guard (added in roadmap 7.2.3.1)
  must continue to pass with the new module in scope.
- **100% docstring coverage (`interrogate fail-under = 100`).** Every public
  module, class, function, `__init__`, magic method, nested function, and
  private symbol the factory introduces must carry a docstring. `interrogate`
  is AST-based: it reads source, it does not import. Therefore the four concrete
  error classes **must be defined with literal `class` statements carrying
  literal docstrings** in `errors.py`; they must not be synthesised at runtime
  with `type(...)`, which `interrogate` cannot see and which would also break
  the Sphinx `:class:` cross-references the `__init__` and test docstrings rely
  on. (See Decision D-STATIC-CLASSES.)
- **Quality gate.** `make all` (build, check-fmt, lint, typecheck, test) must
  pass. Markdown changes additionally require `make markdownlint` and `make
  nixie`. Prose is en-GB Oxford spelling ("-ize"/"-yse"/"-our").

## Tolerances (exception triggers)

- **Scope:** if the implementation touches more than 12 files or more than ~300
  net lines, stop and escalate. (Expected: `loaderkit/errors.py` new;
  `loaderkit/__init__.py`, `rulepack/errors.py`, `ledger/errors.py` edited; one
  new test file; optionally the developers' guide. ≈6 files.)
- **Interface:** if preserving the public surface forces *any* change to a class
  name, the `rule_id`/`device_id` keyword or attribute name, the
  `EnvelopeMessagesError` base, or a message string, stop and escalate — that is
  a behaviour change, not a refactor.
- **Dependencies:** if any new third-party dependency seems required, stop and
  escalate. None is expected; this is stdlib-only.
- **Iterations:** if `make all` still fails after 3 fix attempts on the same
  work item, stop and escalate with the failure transcript.
- **Snapshot drift:** if any syrupy snapshot reports a diff, stop and escalate —
  a snapshot change means a message or shape regressed; do not accept it.
- **Ambiguity:** the one genuine fork — whether the shared shape is delivered as
  a *base class the four classes subclass* versus a *callable factory returning
  classes* — is resolved in this plan (Decision D-STATIC-CLASSES, base-class
  variant). If implementation reveals that variant cannot satisfy a constraint,
  stop and escalate rather than switching mechanisms silently.

## Risks

- Risk: a runtime class-synthesis factory (`type(name, bases, ns)` or a
  closure returning a class) would defeat `interrogate` (no AST-visible
  docstrings), break the Sphinx `:class:` cross-references, and obscure
  `isinstance`/`except` for readers.
  Severity: high.
  Likelihood: high (it is the obvious naive reading of "factory").
  Mitigation: Decision D-STATIC-CLASSES mandates literal `class` statements
  with literal docstrings; the shared shape is a *base mixin* the four
  classes subclass, not a synthesised product. Work item 1's test imports
  each concrete class by its real name and asserts `__name__`, base, and
  docstring presence.
- Risk: the id keyword differs per package (`rule_id` vs `device_id`), so a
  single shared `__init__` cannot literally name both. A generic
  `offending_id=` parameter would change the public constructor keyword and
  break every `RulePackError(msg, rule_id=...)` call site.
  Severity: high.
  Likelihood: medium.
  Mitigation: the shared base provides the *storage and message* mechanics
  via a keyword-neutral helper; each concrete subclass keeps a thin literal
  `__init__(self, *messages, rule_id=None)` (resp. `device_id`) that records
  the attribute under the public name and delegates the messages to the base.
  The factory's value is the de-duplicated base behaviour and the
  file-error class, not the elimination of the two tiny id-bearing inits.
  Work item 1 pins both keyword names by construction in the test.
- Risk: `RulePackError` and `LedgerError` accidentally become the same class
  (or share a base that a too-broad `except` catches), so a rule-pack
  command swallows a ledger error or vice versa.
  Severity: medium.
  Likelihood: low.
  Mitigation: the four classes remain four distinct `class` statements; the
  shared base is an *internal* `loaderkit.errors` mixin that is **not** in
  either package's catch list. Work item 1 asserts
  `not issubclass(RulePackError, LedgerError)` and that neither file-error is
  a subclass of the other's content error.
- Risk: the new `loaderkit/errors.py` module imports `EnvelopeMessagesError`
  from `contract` but a future reader adds a pack import, reintroducing a
  cycle.
  Severity: low.
  Likelihood: low.
  Mitigation: the roadmap-7.2.3.1 parametrised import-direction guard walks
  every `loaderkit` module; confirm it now covers `errors.py` (it globs the
  package, so it should pick the new module up automatically) and add an
  explicit assertion in the new test if it does not.

## Progress

- [x] Work item 1: introduce `loaderkit/errors.py` with the shared
  error-hierarchy factory and its focused unit test (red → green).
- [x] Work item 2: rebind `rulepack/errors.py` onto the factory, keeping the
  four public names, docstrings, and the `rule_id` keyword.
- [x] Work item 3: rebind `ledger/errors.py` onto the factory, keeping the
  four public names, docstrings, and the `device_id` keyword.
- [x] Work item 4: export the factory from `loaderkit/__init__`, extend the
  import-direction guard coverage assertion, and record the consolidation in
  the developers' guide.

## Surprises & discoveries

- Work item 1: the minimal base mechanism is *no* mechanism — `PackError` adds
  nothing to `EnvelopeMessagesError` beyond being a named, distinct base, because
  each per-family `__init__` already calls the inherited
  `EnvelopeMessagesError.__init__(*messages)` and assigns its own id attribute in
  one line. The keyword-neutral helper foreseen in D-BASE-MIXIN proved
  unnecessary, so it was dropped (decision updated in place).
- Work item 1: the loaderkit import-direction guard
  (`tests/test_loaderkit_scan.py::test_loaderkit_module_imports_no_pack_domain`)
  globs `loaderkit/*.py`, so it picked up `errors.py` automatically; no fixed
  list needed amending.

## Decision log

- Decision (D-STATIC-CLASSES): the four concrete error classes stay literal
  `class` statements with literal docstrings in their `errors.py` modules;
  the shared factory is a **base mixin** (plus a helper for the file-error
  class) they subclass, not a runtime `type()` synthesiser.
  Rationale: `interrogate fail-under = 100` is AST-based and cannot see a
  runtime-synthesised class's docstrings; the Sphinx `:class:` cross-
  references in `tests/*` and the `__init__` docstrings target real,
  importable, named classes; and `isinstance`/`except`/`issubclass` readers
  need the names visible at definition sites. This mirrors how 7.2.2/7.2.3
  realised "parameterised on an error factory" — the shared *body* moves to
  `loaderkit`, the per-package *binding* stays thin and named at the leaf.
  Date/Author: 2026-06-27, planning agent.
- Decision (D-BASE-MIXIN): the shared shape is delivered as
  `loaderkit.errors.PackError` (the content-error base, subclassing
  `EnvelopeMessagesError`, providing shared `messages` storage so the
  id-bearing subclass body is one line) and `loaderkit.errors.PackFileError`
  (the file-error base, a bare `EnvelopeMessagesError` subclass with a
  docstring slot for the noun). The two content-error subclasses keep a
  literal `__init__(self, *messages, rule_id=None)` / `(…, device_id=None)`
  that assigns the public attribute and calls the base; the two file-error
  subclasses are empty-bodied `class X(PackFileError): "<doc>"`.
  Rationale: this removes the duplicated base wiring and the `*FileError`
  near-copy while keeping the per-package keyword name a one-line literal,
  not a generic `offending_id`. The factory earns its keep by owning the
  base behaviour and the file-error shape, which is what a third family
  reuses. Implementation settled the base API as plain subclassing: the
  per-family `__init__` calls the inherited
  `EnvelopeMessagesError.__init__(*messages)` directly, so `PackError` adds
  no helper method — the de-duplicated value is the base wiring and the
  file-error class, not an extra mechanism (see Work item 1).
  Date/Author: 2026-06-27, planning agent.
- Decision (D-NO-EXTERNAL-RESEARCH): this task touches no `cuprum`-driven
  shell execution and no locked external library behaviour (Cyclopts,
  pytest-timeout, uv resolution). The only tooling contracts that bind the
  mechanism are `interrogate` (AST docstring coverage), Ruff lint, and `ty`
  typecheck — all already gated by `make all` and verified by running it.
  The `cuprum` source pinning and firecrawl library research the workflow
  asks for are therefore not applicable; the load-bearing claim
  ("`interrogate` is AST-based, so synthesised classes fail the 100% gate")
  is pinned by Work item 1's `make lint` run, not asserted from memory.
  Date/Author: 2026-06-27, planning agent.

## Outcomes & retrospective

- All four work items landed as atomic gated commits with `make all` green at
  each. `novel_ralph_skill/loaderkit/errors.py` now owns the `PackError` /
  `PackFileError` two-class shape; `rulepack/errors.py` and `ledger/errors.py`
  bind it by subclassing, keeping their four public names, the
  `rule_id`/`device_id` keywords, and every message string. No call site, catch
  site, `_coerce` binding, `__all__` entry, or pre-existing test changed, and no
  syrupy snapshot drifted (`--snapshot-update` was never run).
- Scope held inside the Tolerance: six files touched
  (`loaderkit/errors.py` new, `loaderkit/__init__.py`, `rulepack/errors.py`,
  `ledger/errors.py`, `tests/test_loaderkit_errors.py` new,
  `docs/developers-guide.md`) plus this ExecPlan and its review artefact.
- The neutral-leaf invariant holds: `loaderkit.errors` imports only
  `contract.errors`. The package-wide glob guard in
  `tests/test_loaderkit_scan.py` covers `errors.py` automatically, and a focused
  belt-and-braces assertion in `tests/test_loaderkit_errors.py` pins it directly.
- CodeRabbit: work item 1 raised three findings (a base-keyword negative test,
  ExecPlan list indentation, and second-person voice), all addressed; work items
  2-4 returned zero findings. Work item 3's review hit a CodeRabbit rate limit
  and cleared after exponential backoff (30s/60s/120s/240s/480s).
- `interrogate` stayed at 100%: the four concrete classes remain literal `class`
  statements with literal docstrings (Decision D-STATIC-CLASSES held).

## Context and orientation

You are working in the git worktree at
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-2-5` on branch
`roadmap-7-2-5`. Use absolute paths. Do not edit anything outside this worktree.

The package under change is `novel_ralph_skill`, a Python deterministic harness.
The relevant layering (design §3.1, §6; `docs/adr-003-shared-interface-contract.md`):

- `novel_ralph_skill/contract/errors.py` defines `EnvelopeMessagesError`, the
  base every domain error subclasses. Its constructor is
  `__init__(self, *messages: str)` and it records `self.messages: tuple[str,
  ...] = messages`. This is the bottom of the dependency graph; everything may
  depend on it.
- `novel_ralph_skill/loaderkit/` is a *neutral leaf* package that depends only
  on `contract` and the standard library. It owns the schema-agnostic loader
  primitives both pack families share: `coerce.py` (the `CoercionErrors` bundle
  plus `where`/`require*`/`reject_unknown_keys`), `load.py`
  (`entries`/`compile_pattern`/`reject_duplicate_ids`/`load_toml`), and
  `scan.py` (`scan_pattern` plus `ScannedChapter`/`LineHit`). **It does not yet
  own the error hierarchy** — that is this task. Neither `rulepack` nor `ledger`
  may be imported here, ever (the roadmap-7.2.3.1 guard enforces this).
- `novel_ralph_skill/rulepack/errors.py` defines `RulePackError(*messages,
  rule_id=None)` and `RulePackFileError(*messages)`, both subclassing
  `EnvelopeMessagesError`. `RulePackError` stores `self.rule_id`.
- `novel_ralph_skill/ledger/errors.py` is the structural twin: `LedgerError(…,
  device_id=None)` storing `self.device_id`, and `LedgerFileError`.

Who consumes them (do not break these):

- Raise sites: `rulepack/parse.py` (×6 `RulePackError`, ×1 `RulePackFileError`
  via `load_toml`'s `file_error=`), `ledger/_fields.py` (×6 `LedgerError`),
  `ledger/parse.py` (×2 `LedgerError`, ×1 `LedgerFileError` via `load_toml`).
- Bindings: `rulepack/_coerce.py` and `ledger/_coerce.py` build a
  `CoercionErrors` bundle whose `content_error` lambda constructs the content
  error with the package's id keyword.
- Catch sites: `commands/_desloppify.py`, `commands/_desloppify_ledger.py`.
- Re-exports: `rulepack/__init__.py` and `ledger/__init__.py` `__all__`.
- Tests: `tests/test_rulepack_loader.py`, `tests/test_rulepack_schema.py`,
  `tests/test_ledger_command.py`, `tests/test_ledger_detect.py`,
  `tests/test_ledger_properties.py`, `tests/test_ledger_snapshots.py`,
  `tests/test_contract_errors.py`, the cross-command contract snapshots, and
  the e2e error-arm test all import these by name and assert on
  `.rule_id`/`.device_id`/`.messages` and exit codes.

The precedent to mirror is roadmap 7.2.2/7.2.3: the shared *body* lives once in
`loaderkit`, each package keeps a thin named *binding*. The developers' guide
section "The shared loader primitives (`loaderkit`)"
(`docs/developers-guide.md`, around line 1779) and design §6.1/§6.2/§6.3 record
this; `docs/execplans/roadmap-7-2-2.md` (Decision D-FACTORY) records why the
error channels were scoped out then and left for exactly this task.

Terms:

- *Content error* — the exit-2 channel for malformed *content* (`RulePackError`
  / `LedgerError`), carrying an optional offending-entity id.
- *File error* — the exit-3 channel for an absent/unreadable/undecodable *file*
  (`RulePackFileError` / `LedgerFileError`), carrying only `messages`.
- *Binding* — a thin per-package module that adapts a shared `loaderkit` body to
  that package's typed channel and nouns, introduced for coercion by 7.2.2.

## Plan of work

The work proceeds in four atomic, independently committable, gate-passable work
items. Each ends with `make all` green. Items 2 and 3 are symmetric and could be
done in either order; item 1 must precede both; item 4 is last.

### Stage A — understand and propose (no code changes)

Read, in this order: `novel_ralph_skill/contract/errors.py` (the base
constructor); both current `errors.py` modules (the exact docstrings and the id
kwarg); `novel_ralph_skill/loaderkit/coerce.py` and `loaderkit/load.py` (the
established factory-binding style and the `file_error=` callable contract);
`tests/test_loaderkit_coerce.py` (the sentinel-bundle test idiom to copy);
`tests/test_rulepack_loader.py` and a ledger error test (the `.rule_id` /
`.device_id` assertions you must not break). Confirm the import-direction guard
file (search `tests/` for `test_loaderkit*import*` or the parametrised guard
from roadmap 7.2.3.1) globs the whole `loaderkit` package so it will include
`errors.py` automatically. Go/no-go: if the base `EnvelopeMessagesError.__init__`
signature differs from `(*messages)`, re-derive the base-mixin shape before
coding.

### Work item 1 — introduce `loaderkit/errors.py` and pin it (red → green)

Create `novel_ralph_skill/loaderkit/errors.py`. It imports only
`from novel_ralph_skill.contract.errors import EnvelopeMessagesError` and the
standard library. Define the shared shape per Decision D-BASE-MIXIN:

- `PackError(EnvelopeMessagesError)` — the content-error base. It provides the
  shared mechanics so each concrete subclass's `__init__` is one line: a method
  (for example `_with_offending_id(self, messages, offending_id)`) or simply the
  inherited `EnvelopeMessagesError.__init__(*messages)` plus a documented
  contract that subclasses set their public id attribute. Pick the *minimal*
  mechanism that lets `RulePackError`/`LedgerError` keep a literal
  `__init__(self, *messages, rule_id=None)` body that records the public
  attribute and delegates messages to the base. Carry a module docstring and a
  class docstring.
- `PackFileError(EnvelopeMessagesError)` — the file-error base: a documented
  empty subclass the two concrete file errors inherit, so the duplicated
  "absent/unreadable/undecodable file → exit 3" shape lives once. Carry a class
  docstring describing the exit-3 channel in noun-neutral terms.

Do **not** import or reference any rule-pack/ledger nouns or types here.

Write `tests/test_loaderkit_errors.py` first (it fails until the module exists),
mirroring the sentinel idiom in `tests/test_loaderkit_coerce.py`. It must pin:

1. A test-local `class _SampleError(PackError)` with `__init__(self, *messages,
   sample_id=None)` records `self.sample_id` and `self.messages`, proving the
   base supports a per-family id keyword of arbitrary name (the third-family
   contract). Assert both the stored id and `.messages` tuple.
2. A test-local `class _SampleFileError(PackFileError)` constructs from
   `*messages` only, records `.messages`, and is callable as `file_error(msg)`
   (a one-arg call), proving it satisfies `load_toml`'s `Callable[[str],
   EnvelopeMessagesError]` contract.
3. `issubclass(PackError, EnvelopeMessagesError)` and
   `issubclass(PackFileError, EnvelopeMessagesError)`, and that `PackError` and
   `PackFileError` are *distinct* (neither subclasses the other), so a content
   catch and a file catch stay separable.

These tests pin the factory so a third pack family inherits the primitive (the
roadmap Success criterion). Run `uv run pytest tests/test_loaderkit_errors.py`
(red before the module, green after), then `make all`.

Cited: design §6.1/§6.3 (`loaderkit` neutral home);
`docs/adr-003-shared-interface-contract.md` (acyclic layering);
`docs/execplans/roadmap-7-2-2.md` Decision D-FACTORY (the error-factory framing
this completes); AGENTS.md "Python verification and testing" (unit tests, 100%
docstrings).

### Work item 2 — rebind `rulepack/errors.py` onto the factory

Rewrite `novel_ralph_skill/rulepack/errors.py` so `RulePackError` subclasses
`loaderkit.errors.PackError` and `RulePackFileError` subclasses
`loaderkit.errors.PackFileError`. Keep:

- the two literal `class` statements and their existing module/class/`__init__`
  docstrings (retune only wording that referenced the now-shared base, keeping
  en-GB Oxford spelling and the design-§ citations);
- `RulePackError.__init__(self, *messages: str, rule_id: str | None = None)`
  recording `self.rule_id`;
- `RulePackFileError` with no extra constructor (inherits the `*messages`
  shape).

No call site, binding, catch site, `__all__` entry, or test changes. Run the
rule-pack suites explicitly — `uv run pytest tests/test_rulepack_loader.py
tests/test_rulepack_schema.py tests/test_rulepack_detect.py
tests/test_rulepack_properties.py tests/test_contract_errors.py` — they must
pass unchanged, then `make all`.

Cited: design §6.1; `docs/adr-003-shared-interface-contract.md`;
`docs/execplans/roadmap-7-2-2.md` (the binding precedent);
`novel_ralph_skill/rulepack/errors.py`.

### Work item 3 — rebind `ledger/errors.py` onto the factory

The symmetric change for `novel_ralph_skill/ledger/errors.py`: `LedgerError`
subclasses `PackError` with `__init__(self, *messages, device_id=None)` storing
`self.device_id`; `LedgerFileError` subclasses `PackFileError`. Preserve the
existing docstrings (including the "mirroring `rulepack/errors.py`" note —
update it to point at the shared `loaderkit.errors` base). No call site,
binding, catch site, `__all__`, or test changes. Run the ledger suites — `uv run
pytest tests/test_ledger_command.py tests/test_ledger_detect.py
tests/test_ledger_properties.py tests/test_ledger_snapshots.py` — unchanged,
then `make all`.

Cited: design §6.3; `docs/adr-003-shared-interface-contract.md`;
`novel_ralph_skill/ledger/errors.py`.

### Work item 4 — export, guard, and document

- In `novel_ralph_skill/loaderkit/__init__.py`, export `PackError` and
  `PackFileError` from `loaderkit.errors` and add them to `__all__`
  (alphabetically, matching the existing list style), so the shared shape is a
  first-class `loaderkit` primitive beside `CoercionErrors`.
- Confirm the roadmap-7.2.3.1 parametrised import-direction guard now exercises
  `loaderkit/errors.py`. If it discovers modules by walking the package it will
  already; if it enumerates a fixed list, add `errors` to it. Either way, add an
  explicit assertion in `tests/test_loaderkit_errors.py` that
  `loaderkit.errors` imports no `rulepack`/`ledger` symbol (a focused belt-and-
  braces pin matching the neutral-leaf invariant), if the global guard does not
  already cover it.
- Update the developers' guide section "The shared loader primitives
  (`loaderkit`)" (`docs/developers-guide.md`, ~line 1779): add the error
  hierarchy to the list of primitives `loaderkit` now owns and record that each
  package binds `PackError`/`PackFileError` for its typed channel, mirroring the
  coercion binding. This is a docs change, so additionally run `make
  markdownlint` and `make nixie`.

Cited: design §6.1/§6.3; `docs/adr-003-shared-interface-contract.md`;
AGENTS.md (documentation update obligation); `docs/developers-guide.md`.

### Stage D — hardening

After item 4, run the full `make all` once more, plus `make markdownlint` and
`make nixie` for the touched markdown. Confirm no snapshot drift and no
`interrogate` shortfall. Update Progress, Surprises, and Outcomes.

## Concrete steps

Run all commands from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-2-5`.

1. Work item 1 — create the module and its test, confirm red then green:

        uv run pytest tests/test_loaderkit_errors.py
        # before the module exists: collection/import error or failures
        # after writing loaderkit/errors.py: N passed
        make all

   Expected tail of `make all`: all suites pass; `interrogate` reports 100%;
   Ruff and `ty` clean.

2. Work item 2 — rebind rulepack, then:

        uv run pytest tests/test_rulepack_loader.py tests/test_rulepack_schema.py \
          tests/test_rulepack_detect.py tests/test_rulepack_properties.py \
          tests/test_contract_errors.py
        make all

   Expected: every test passes unchanged (no edits to these test files).

3. Work item 3 — rebind ledger, then:

        uv run pytest tests/test_ledger_command.py tests/test_ledger_detect.py \
          tests/test_ledger_properties.py tests/test_ledger_snapshots.py
        make all

   Expected: passes unchanged; no `.ambr` snapshot diff.

4. Work item 4 — export, guard, document, then:

        make all
        make markdownlint
        make nixie

Format only the files you changed before each commit: run the markdown
formatter on the specific docs path you touched (`mdtablefix
docs/developers-guide.md` then `markdownlint-cli2 --fix docs/developers-guide.md`)
and `make markdownlint`/`make nixie`; do **not** run a repo-global format that
churns unrelated files. Commit after each work item with a gated commit.

## Validation and acceptance

Acceptance is behavioural and observable:

- **Single home.** `novel_ralph_skill/loaderkit/errors.py` exists and owns the
  two-class hierarchy shape (`PackError` + `PackFileError`); `git grep -n
  "class .*Error(EnvelopeMessagesError)" novel_ralph_skill/rulepack/errors.py
  novel_ralph_skill/ledger/errors.py` shows the concrete classes now subclass
  the `loaderkit.errors` bases, not `EnvelopeMessagesError` directly.
- **No regressions.** `make all` is green. The new test
  `tests/test_loaderkit_errors.py` fails before `loaderkit/errors.py` exists and
  passes after. Every pre-existing rule-pack and ledger suite passes **without
  edits**, proving the public surface (class names, `rule_id`/`device_id`
  keyword and attribute, exit-code mapping via the catch sites, message strings)
  is unchanged.
- **No snapshot drift.** No `.ambr` file changes; `--snapshot-update` was not
  run.
- **Neutral leaf preserved.** The `loaderkit` import-direction guard passes with
  `errors.py` in scope; `loaderkit.errors` imports no pack symbol.
- **Documented single source of truth.** The developers' guide records the error
  hierarchy as a `loaderkit`-owned primitive each package binds.

Quality criteria ("done"):

- Tests: `make test` green; `tests/test_loaderkit_errors.py` is the new pin; all
  rulepack/ledger/contract suites green unchanged.
- Lint/typecheck: `make lint` (Ruff + `interrogate` 100% + Pylint) and `make
  typecheck` (`ty`) clean.
- Markdown: `make markdownlint` and `make nixie` clean for the touched guide.

Quality method: `make all` for code; `make markdownlint` + `make nixie` for
markdown. No new dependency, no behaviour change.

## Idempotence and recovery

Each work item is a self-contained edit ending in a gated commit, so the tree is
clean between items and any item can be re-run from a clean checkout. If `make
all` fails mid-item, the failure is local to that item's edit; revert the
working-tree change for that file and re-apply. If a commit must be parked for
formatter churn, name the stash `df12-stash v1 task=roadmap-7-2-5
kind=discard reason="formatter churn"`. No destructive or irreversible step is
involved.

## Artifacts and notes

The two near-copy modules being consolidated:

- `novel_ralph_skill/rulepack/errors.py`: `RulePackError(*messages,
  rule_id=None)` storing `self.rule_id`; `RulePackFileError(*messages)`.
- `novel_ralph_skill/ledger/errors.py`: `LedgerError(*messages,
  device_id=None)` storing `self.device_id`; `LedgerFileError(*messages)`.

The `file_error=` callable contract they must keep honouring
(`novel_ralph_skill/loaderkit/load.py`):

        def load_toml(
            path: Traversable,
            *,
            noun: str,
            file_error: cabc.Callable[[str], EnvelopeMessagesError],
        ) -> dict[str, object]:

## Interfaces and dependencies

At the end of the work the following must exist.

In `novel_ralph_skill/loaderkit/errors.py`:

        from novel_ralph_skill.contract.errors import EnvelopeMessagesError


        class PackError(EnvelopeMessagesError):
            """Shared exit-2 content-error base for every loader family."""
            # minimal shared mechanics so a subclass __init__ recording its own
            # `<family>_id` attribute is one line (see Decision D-BASE-MIXIN).


        class PackFileError(EnvelopeMessagesError):
            """Shared exit-3 file-error base: absent, unreadable, undecodable."""

In `novel_ralph_skill/rulepack/errors.py` (names and keyword unchanged):

        from novel_ralph_skill.loaderkit.errors import PackError, PackFileError


        class RulePackError(PackError):
            def __init__(self, *messages: str, rule_id: str | None = None) -> None: ...


        class RulePackFileError(PackFileError): ...

In `novel_ralph_skill/ledger/errors.py` (symmetric, `device_id`):

        class LedgerError(PackError):
            def __init__(self, *messages: str, device_id: str | None = None) -> None: ...


        class LedgerFileError(PackFileError): ...

`novel_ralph_skill/loaderkit/__init__.py` re-exports `PackError` and
`PackFileError` in `__all__`. No external dependencies are added; the only
imports are `novel_ralph_skill.contract.errors` and the standard library.

## Addenda

- [x] 7.2.5.1 — Pin the real rule-pack/ledger error bindings to the `loaderkit`
  bases and mirror the distinctness assertions (from audit:7.2.5, review:7.2.5;
  medium; three near-identical proposals merged). The success criterion's "a
  test pins it so it cannot silently re-fork" leg is unmet for the *real*
  bindings: `tests/test_loaderkit_errors.py` exercises only synthetic
  test-local subclasses (`_SampleError`/`_SampleFileError`), so no test asserts
  that the concrete `RulePackError`/`RulePackFileError`/`LedgerError`/
  `LedgerFileError` classes actually subclass
  `loaderkit.errors.PackError`/`PackFileError` — the consolidation could
  re-fork while the suite stays green. Separately, `tests/test_contract_errors.py`
  pins the within-family distinctness for the rule pack
  (`not issubclass(RulePackError, RulePackFileError)` both ways) but carries no
  ledger equivalent, and no test pins the cross-family distinctness
  (`not issubclass(RulePackError, LedgerError)`) the Risk-3 mitigation
  references. Scope: add concrete-binding subclass assertions for all four real
  classes against `PackError`/`PackFileError`; add a ledger mirror of the
  rule-pack within-family distinctness pins; add a cross-family distinctness
  pin. One focused test-only commit; structurally guaranteed today by the
  separate `class` statements, so the value is regression-proofing a future
  hand-edit that re-forks a binding or re-parents an error. Lightweight
  addendum pass.
