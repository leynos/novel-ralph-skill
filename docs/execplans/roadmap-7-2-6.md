# Consolidate the rule-pack and device-ledger validating parse boundaries onto a shared `loaderkit` skeleton

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: IMPLEMENTED (all four work items landed; `make all` green at HEAD with no
snapshot drift; see Outcomes & retrospective for the two recorded deviations)

## Purpose / big picture

The rule-pack loader (`novel_ralph_skill/rulepack/parse.py`) and the
device-ledger loader (`novel_ralph_skill/ledger/parse.py`) each carry a
structurally identical *validating parse boundary*: a pure `parse_*` function
that rejects an unknown top-level key, resolves and rejects an unsupported
`schema_version`, extracts the non-empty entry array, builds one validated
entry per array element, rejects duplicate ids, and constructs the frozen
result dataclass. The two copies of that orchestration differ only in five
particulars: the schema-version constant (`RULEPACK_SCHEMA_VERSION` versus
`LEDGER_SCHEMA_VERSION`), the top-level key set (`_PACK_KEYS` versus
`_LEDGER_KEYS`), the entry-array key (`"rule"` versus `"device"`), the
per-entry projection (`_rule` versus `_device`), and the result-type
construction (`RulePack(schema_version, pack, rules)` versus
`DeviceLedger(schema_version, devices)`, the rule pack carrying one extra
top-level string field, `pack`).

This is the same near-copy that roadmap task 7.2.2 retired for the *coercion*
and *scan* bodies and task 7.2.5 retired for the *error hierarchies*, both by
lifting the shared body into `loaderkit` and leaving each package a thin
*binding*. The parse boundary is the last un-consolidated loader primitive: no
existing roadmap task covers it (7.3.9 targets command bodies, 7.8.2 targets
the detector scan-aggregate), and there is no drift guard, so a hand-edit to one
`parse_*` can silently diverge from the other.

After this change a maintainer adding a third loader family (the per-novel packs
foreshadowed in design §8.1, the seam roadmap 8.1.9 already assumes) *binds* one
shared parse skeleton — supplying its constant, key set, array key, per-entry
builder, and a result constructor — rather than hand-copying a third
`parse_*`/`_rule`/`_device` orchestration. Success is observable three ways:
(1) `novel_ralph_skill/loaderkit/parse.py` exists and owns the schema-version
resolve-and-reject block, the entry-array extraction call, the per-entry build
loop, and the duplicate-id rejection, and `parse_rulepack`/`parse_ledger` are
each a thin call into it; (2) every existing rule-pack and ledger suite passes
**without edits**, proving the public surface (the `parse_*`/`load_*` function
names and signatures, each typed error channel, the `rule_id`/`device_id`
keyword, the exit-code mapping, and every operator message) is unchanged; and
(3) a new `tests/test_loaderkit_parse.py` pins the skeleton against a test-local
third-family binding so a third pack inherits it instead of cloning a third
copy.

The public surface — the `parse_rulepack`/`load_rulepack`/`parse_ledger`/
`load_ledger` names (re-exported from each package `__init__`), their
signatures, the four error types, the `rule_id`/`device_id` keyword and
attribute, the exit-code mapping the command layer performs, and every
operator-facing message string — is unchanged. This is a pure internal
refactor: no behaviour changes, no snapshot regeneration.

## Constraints

Hard invariants that must hold throughout. Violation requires escalation, not a
workaround.

- **No behaviour change, no message change, no snapshot regeneration.** The
  loaders must raise the same error *types* carrying the same `messages` tuples
  and the same `rule_id`/`device_id` values for every malformed-content fault
  class (unknown key, missing/wrong-typed `schema_version`, unsupported version,
  absent/empty/non-mapping entry array, malformed entry, duplicate id), so every
  command-layer `except RulePackError`/`except LedgerError` arm and every syrupy
  snapshot under `tests/__snapshots__/` and
  `tests/cross_command_contract/__snapshots__/` stays byte-identical. The two
  unsupported-version sentences (`"unsupported rule-pack schema_version {n};
  expected {m}"` and `"unsupported device-ledger schema_version {n}; expected
  {m}"`) carry a per-family noun (`rule-pack`/`device-ledger`) the skeleton must
  receive as a parameter, not hard-code. Do **not** run `--snapshot-update`.
- **The exact per-family fault precedence is preserved, including the rule
  pack's `pack`-read position.** `parse_rulepack` reads the top-level `pack`
  string **before** it extracts the `rule` array (live order: reject-unknown-keys
  → require `schema_version` → version check → require `pack` → `entries` → build
  → reject-duplicate-ids). For an input that is *simultaneously* missing `pack`
  and carrying an absent/empty/non-mapping/malformed `rule` array, the original
  raises the **missing-`pack`** `RulePackError`, not the entry-array one. This
  precedence is unguarded by the current corpus (no fixture combines the two
  faults: `missing-pack.toml` carries a valid one-rule array;
  `missing-rule-array.toml` and `empty-rule-array.toml` both carry a valid
  `pack`; the property generators mutate one field of a well-formed pack and never
  drop `pack` while corrupting the array), so the refactor must **not** lean on
  the suites passing to prove it; it must reproduce the `pack`-before-`entries`
  order structurally and add a fixture/test pinning it (see Decision
  D-SKELETON-HEAD-TAIL and Work item 2). The ledger has no top-level string
  field, so there is no analogous interleave and no precedence question on its
  side (Work item 3).
- **The `parse_*`/`load_*` names and signatures are public and must be
  preserved.** `parse_rulepack(raw)`, `load_rulepack(path)`, `parse_ledger(raw)`,
  and `load_ledger(path)` are re-exported in `novel_ralph_skill/rulepack/__init__`
  and `novel_ralph_skill/ledger/__init__` `__all__`. They must keep their exact
  names, parameter names, type hints, and return types
  (`RulePack`/`DeviceLedger`), and remain importable both as
  `novel_ralph_skill.rulepack.parse.parse_rulepack` and from the package root.
  `load_*` must keep delegating to `parse_*` over the `load_toml` file-error
  channel unchanged.
- **The result-type construction is per-family and must not move into
  `loaderkit`.** `RulePack` and `DeviceLedger` (and `Rule`/`Device`) live in each
  pack's `schema.py`; `loaderkit` must never import them. The skeleton therefore
  receives the result constructor as a caller-supplied callable and the entry
  builder as a caller-supplied callable, never naming a pack type. The rule
  pack's extra top-level `pack` string field is read **at the rule-pack call
  site**, not by the skeleton, because the ledger has no such field (see
  Decision D-RESULT-CALLBACK).
- **The per-entry builder stays per-family and keeps its `index=` contract.**
  `_rule(entry, *, index)` and `_device(entry, *, index)` carry pack-specific
  field validation (`_resolve_basis`/`_resolve_page_words` for the rule pack;
  `_rationing_fields` for the ledger) and each names the offending entry's array
  `index` when its `id` is absent. The skeleton must call the caller's builder
  with `(entry, index=index)` for each entry in authoring order, never inlining
  any field logic, so the per-entry projection stays a one-line binding at the
  leaf.
- **`loaderkit` stays a neutral leaf.** `novel_ralph_skill/loaderkit/parse.py`
  must import nothing from `rulepack` or `ledger` — at runtime or under
  `TYPE_CHECKING` — exactly as the other `loaderkit` modules do (design §6, §6.1,
  §6.3; `docs/adr-003-shared-interface-contract.md`). It may depend only on
  `novel_ralph_skill.contract.errors`, `novel_ralph_skill.loaderkit` siblings
  (`coerce`, `load`), and the standard library. The parametrized package-wide
  import-direction guard
  (`tests/test_loaderkit_scan.py::test_loaderkit_module_imports_no_pack_domain`,
  which globs `loaderkit/*.py`) must continue to pass with the new module in
  scope.
- **100% docstring coverage (`interrogate fail-under = 100`).** Every public
  module, class, function, `__init__`, and private symbol the skeleton introduces
  must carry a docstring. `interrogate` is AST-based: it reads source, it does
  not import. Any dataclass bundle the skeleton introduces must be a literal
  `class`/`@dataclass` statement with a literal docstring, not a runtime
  synthesizer (mirroring Decision D-STATIC-CLASSES in
  `docs/execplans/roadmap-7-2-5.md`).
- **No file exceeds 400 lines (AGENTS.md "Keep file size manageable").** After
  the refactor each `parse.py` shrinks; the new `loaderkit/parse.py` must stay
  under the cap. None is at risk (rulepack/parse.py is 304 lines and shrinks;
  ledger/parse.py is 226 and shrinks).
- **Quality gate.** `make all` (build, check-fmt, lint, typecheck, test) must
  pass. Markdown changes additionally require `make markdownlint` and `make
  nixie`. Prose is en-GB Oxford spelling ("-ize"/"-yse"/"-our").

## Tolerances (exception triggers)

- **Scope:** if the implementation touches more than 10 files or more than ~320
  net lines, stop and escalate. (Expected: `loaderkit/parse.py` new;
  `loaderkit/__init__.py`, `rulepack/parse.py`, `ledger/parse.py` edited; one new
  test file `tests/test_loaderkit_parse.py`; one new fixture
  `tests/data/rulepacks/missing-pack-and-empty-array.toml` plus an added test in
  `tests/test_rulepack_loader.py` pinning the rule pack's `pack`-before-`entries`
  precedence; the developers' guide. ≈8 files. The `tests/test_rulepack_loader.py`
  edit only **adds** a case — it modifies no existing assertion; if preserving the
  public surface forced a change to any *existing* test assertion, that would be
  an Interface-tolerance breach, not this addition.)
- **Interface:** if preserving the public surface forces *any* change to a
  `parse_*`/`load_*` name or signature, an error type, the `rule_id`/`device_id`
  keyword or attribute, the result dataclass shape, or a message string, stop and
  escalate — that is a behaviour change, not a refactor.
- **Dependencies:** if any new third-party dependency seems required, stop and
  escalate. None is expected; this is stdlib-plus-`loaderkit`-only.
- **Iterations:** if `make all` still fails after 3 fix attempts on the same work
  item, stop and escalate with the failure transcript.
- **Snapshot drift:** if any syrupy snapshot reports a diff, stop and escalate —
  a snapshot change means a message or shape regressed; do not accept it. Do not
  run `--snapshot-update`.
- **Ambiguity:** two forks are resolved in this plan and must not be silently
  re-litigated. (1) Whether the skeleton constructs the result dataclass itself
  (impossible without importing pack types) versus leaving the per-family
  `RulePack`/`DeviceLedger` construction at each leaf — resolved by Decision
  D-RESULT-CALLBACK (construction stays at the leaf). (2) Whether the skeleton is
  one all-in-one call or a head/tail pair — resolved by Decision
  D-SKELETON-HEAD-TAIL (a head/tail pair, so the rule pack reads `pack` at the
  original seam and preserves precedence). If implementation reveals that either
  resolution cannot satisfy a Constraint — in particular if the head/tail seam
  cannot reproduce the `pack`-before-`entries` precedence — stop and escalate
  rather than switching mechanisms or accepting a precedence change silently.

## Risks

- Risk: the skeleton tries to construct `RulePack`/`DeviceLedger` itself, which
  forces a `loaderkit → rulepack`/`ledger` import and reintroduces the cycle the
  neutral-leaf invariant forbids.
  Severity: high.
  Likelihood: high (the naive reading of "owns the build loop").
  Mitigation: Decision D-RESULT-CALLBACK — the skeleton returns, or hands to a
  caller-supplied constructor, only the *neutral* products (the resolved
  `schema_version` int and the built entry tuple); the pack type is constructed
  at the call site. Work item 1's test builds a test-local result type with no
  pack import, proving the skeleton names no pack type.
- Risk: the rule pack's extra top-level `pack` string field has no ledger
  analogue, so a skeleton signature that names `pack` cannot serve the ledger,
  and one that ignores it cannot serve the rule pack.
  Severity: high.
  Likelihood: medium.
  Mitigation: the skeleton owns only the family-invariant orchestration (unknown
  key, schema-version, entries, build loop, duplicate ids) and hands the neutral
  products to a per-family result callback; the rule-pack callback reads `pack`
  via `_require_str` at its own call site, the ledger callback ignores it. The
  `pack` read stays in `rulepack/parse.py`. Work item 1 pins a third-family
  binding *without* an extra field and Work item 2 pins one *with* an extra
  field, so both shapes are exercised.
- Risk: folding the whole orchestration into one skeleton call inverts the rule
  pack's `pack`-before-`entries` fault precedence (the round-1 blocking defect):
  a single call can only place the call site's `pack` read before or after the
  whole skeleton, never at the original mid-orchestration seam, so a
  simultaneously missing-`pack` + bad-array input would raise the entry-array
  fault instead of the missing-`pack` fault — a message change the current corpus
  cannot catch.
  Severity: high.
  Likelihood: high (the naive "one shared call" reading).
  Mitigation: Decision D-SKELETON-HEAD-TAIL splits the skeleton into a `head`
  (unknown-keys + schema-version resolve) and a `tail` (entries + build +
  dup-ids); Work item 2 reads `pack` at the seam between them, reproducing the
  exact precedence, and adds `missing-pack-and-empty-array.toml` plus
  `test_missing_pack_precedes_empty_array` to pin it. Work item 1's seam-
  independence test (pin 4) proves the head never reaches the array and the tail
  never inspects the top-level keys/version, so head faults strictly precede tail
  faults.
- Risk: the unknown-key rejection and the unsupported-version sentence both
  carry a per-family noun (`rule pack`/`device ledger` via the `CoercionErrors`
  bundle's `where`; `rule-pack`/`device-ledger` in the version sentence), so a
  skeleton that hard-codes either noun emits the wrong message for one family and
  drifts a snapshot.
  Severity: medium.
  Likelihood: medium.
  Mitigation: the unknown-key rejection already routes through the caller's
  `reject_unknown_keys` (which uses the bundle's nouns), so the skeleton receives
  the `CoercionErrors` bundle and the allowed key set as parameters; the
  unsupported-version *noun* (`"rule-pack"`/`"device-ledger"`) is a distinct
  hyphenated string the bundle does not carry, so it is a separate skeleton
  parameter. Work item 1 pins both version sentences verbatim for both noun sets
  (the prose-pin idiom `tests/test_loaderkit_load.py` established for the
  empty-array strings).
- Risk: `parse_rulepack`'s docstring `Raises` block and the
  `RulePackError`/`LedgerError` "only exception this pure boundary raises"
  invariant could be weakened if the skeleton introduces a new exception path.
  Severity: low.
  Likelihood: low.
  Mitigation: the skeleton raises only through the supplied `CoercionErrors`
  bundle (every fault is already routed through `content_error`), so it
  introduces no new exception type; the `parse_*` docstrings are retuned to cite
  the shared skeleton but keep the "only `*Error`" guarantee. Every existing
  loader suite (which asserts the raised type) must pass unchanged.

## Progress

- [x] Work item 1: introduce `loaderkit/parse.py` with the shared parse skeleton
  as a head/tail pair (`resolve_schema_version` + `build_entries`) and its focused
  unit test (red → green), pinning it against a test-local third-family binding
  with no extra top-level field, including the head/tail seam-independence pin.
- [x] Work item 2: rebind `rulepack/parse.py` onto the head/tail pair, reading
  `pack` at the seam to preserve the `pack`-before-`entries` precedence, keeping
  `parse_rulepack`/`load_rulepack`, the `_rule` builder, and the `RulePack`
  construction at the call site; add `missing-pack-and-empty-array.toml` and a
  precedence regression test. (The `loaderkit/__init__` export — planned for Work
  item 4 — was pulled forward here because the rebind's
  `from novel_ralph_skill.loaderkit import build_entries, resolve_schema_version`
  hard-depends on it; Work item 4 keeps the guard confirmation and the guide
  update.)
- [x] Work item 3: rebind `ledger/parse.py` onto the skeleton, keeping
  `parse_ledger`/`load_ledger`, the `_device` builder, and the `DeviceLedger`
  construction at the call site.
- [x] Work item 4: export the skeleton from `loaderkit/__init__` (done in Work
  item 2, as the rebind hard-depended on it), confirm the import-direction guard
  covers `parse.py` (the glob guard's `[parse.py]` parametrize case passes), and
  record the consolidation in the developers' guide.

## Surprises & discoveries

- Work item 1: the `entry_id` default could not be expressed with `@overload`
  (the planned shape) because three project gates conflict on overloads: the
  repo bans `from typing import overload` (Ruff TID), `interrogate` 1.7.0 does
  not recognize the aliased `@typ.overload` decorator (so it demands a stub
  docstring), and Ruff D418 forbids a docstring on an overload stub. The
  resolution — fully type-safe, no `Any`, no overloads — is to bound the entry
  `TypeVar` to a module-local `_HasId` `Protocol` (`build_entries[T: _HasId]`),
  so the default `_entry_id` (which reads `.id`) type-checks while a family may
  still pass its own `entry_id`. Both real entries (`Rule`/`Device`) and the
  test third family (`_Thing`) satisfy `_HasId`. This preserves the planned
  public shape (a configurable `entry_id` defaulting to `.id`) and the neutral
  leaf, and keeps the 100% docstring gate without a config exemption.

## Decision log

- Decision (D-RESULT-CALLBACK): the shared skeleton owns the family-invariant
  orchestration (reject unknown top-level keys, resolve-and-reject
  `schema_version`, extract the non-empty entry array, build each entry via the
  caller's builder, reject duplicate ids) and returns only *neutral* products —
  the resolved `schema_version` int (from the head) and the built entry `tuple`
  (from the tail) — to the caller, which constructs its own
  `RulePack`/`DeviceLedger`. The skeleton (split per D-SKELETON-HEAD-TAIL) is
  parameterized on: the `CoercionErrors` bundle, the allowed top-level key
  `frozenset`, the schema-version constant, the unsupported-version noun string
  (head); and the entry-array key, the `EntriesMessages` bundle, a per-entry
  builder callable `Callable[[Mapping, int], T]`, and the `entry_id` projection
  (tail). It never imports or names a pack result type.
  Rationale: `RulePack(schema_version, pack, rules)` and
  `DeviceLedger(schema_version, devices)` have different arities (the rule pack
  carries an extra top-level `pack` string), so a skeleton that builds the result
  itself cannot serve both without importing both pack types — violating the
  neutral-leaf invariant (design §6.3, ADR-003). Returning the neutral products
  keeps the per-family construction (and the rule pack's `pack` read) a one-line
  binding at the leaf, exactly mirroring how 7.2.2/7.2.5 kept the per-family
  `_coerce`/`errors` binding thin and named. The skeleton's value is the
  de-duplicated orchestration, not the elimination of the two tiny result
  constructions.
  Date/Author: 2026-06-27, planning agent.
- Decision (D-SKELETON-HEAD-TAIL): the skeleton is split into **two** functions,
  a *head* and a *tail*, rather than one all-in-one call, so the rule-pack call
  site can interleave its `pack` read at the original position — *between* the
  schema-version resolve and the entry-array extraction — and thereby preserve
  the live `pack`-before-`entries` fault precedence (see the Constraints).
  - `resolve_schema_version(raw, *, allowed_keys, schema_version_constant,
    unsupported_noun, errors) -> int` performs, in order: reject unknown
    top-level keys, require `schema_version`, and reject any value `!=
    schema_version_constant` (the version sentence with the per-family hyphenated
    noun). It returns the resolved `schema_version` int. This is the **head**.
  - `build_entries(raw, *, array_key, entries_messages, errors, build_entry,
    entry_id=...) -> tuple[T, ...]` performs, in order: extract the non-empty
    entry array via `entries`, build each entry via the caller's `build_entry`
    callable in authoring order, and reject duplicate ids via
    `reject_duplicate_ids` over the per-family `entry_id` projection (default
    `lambda e: e.id`, so the skeleton names no pack attribute). It returns the
    built entry tuple. This is the **tail**.

  The rule-pack call site runs head → `_require_str(raw, "pack", …)` → tail,
  reproducing the exact original order; the ledger call site runs head → tail
  with no interleave (it has no top-level string field). Both functions are
  generic over the entry element type `T` (a `TypeVar`) and name no pack type or
  noun. The per-family `RulePack`/`DeviceLedger` construction stays a one-line
  binding at each leaf (D-RESULT-CALLBACK).
  Rationale: the round-1 design review found that folding unknown-keys +
  schema-version + entries + build + dup-ids into a *single* skeleton call left
  the rule-pack call site able to place its `pack` read only *before* or *after*
  the whole skeleton — never between the schema-version resolve and `entries`,
  where the original reads it. Placing `pack` after the whole call inverts the
  precedence: for an input simultaneously missing-`pack` + bad-array, the
  original raises the missing-`pack` fault, the all-in-one variant the
  entry-array fault — same type and `rule_id is None`, different message, a
  behaviour change under a "no message change" plan that the current corpus does
  not catch. The two-call
  split is the smallest mechanism that *structurally* preserves the precedence
  (option (a) of the review's required fix) without forcing the precedence change
  of option (b), which would need explicit sign-off. The de-duplication value is
  unchanged: both halves of the shared orchestration still live once in
  `loaderkit`; only the *seam* between them is exposed so the rule pack can read
  `pack` at the seam. Final shape (two free functions versus a tiny class with two
  methods) is a low-risk implementation detail; two free functions match the
  existing `loaderkit` primitive style (`entries`, `reject_duplicate_ids`).
  Date/Author: 2026-06-27, planning agent (revised round 2 to resolve the
  fault-precedence inversion the round-1 review blocked).
  Supersedes: the earlier D-SKELETON-RETURNS-TUPLE (single all-in-one call
  returning `(schema_version, entries)`), withdrawn because it cannot reproduce
  the `pack`-before-`entries` precedence.
- Decision (D-NO-EXTERNAL-RESEARCH): this task touches no `cuprum`-driven shell
  execution and no locked external library behaviour (Cyclopts, pytest-timeout,
  uv resolution). It is a pure internal refactor of two in-process pure functions
  that decode an already-loaded `Mapping`; the only tooling contracts that bind
  the mechanism are `interrogate` (AST docstring coverage), Ruff lint, and `ty`
  typecheck — all already gated by `make all`. The `cuprum` source pinning and
  firecrawl library research the workflow asks for are therefore not applicable;
  the only load-bearing tooling claim ("`interrogate` is AST-based, so a
  runtime-synthesized bundle fails the 100% gate") is pinned by Work item 1's
  `make lint` run, not asserted from memory. This mirrors Decision
  D-NO-EXTERNAL-RESEARCH in `docs/execplans/roadmap-7-2-5.md`, the directly
  preceding consolidation task.
  Date/Author: 2026-06-27, planning agent.

## Outcomes & retrospective

All four work items landed against the Purpose:

- `novel_ralph_skill/loaderkit/parse.py` exists and owns the family-invariant
  orchestration as a head/tail pair (`resolve_schema_version` + `build_entries`);
  `git grep "schema_version !="` over both `parse.py` modules now returns nothing
  (the comparison lives only in the head). Each `parse_*` is a thin
  head→(seam)→tail call plus its per-family result construction.
- Both packages bind the skeleton; the public surface (the `parse_*`/`load_*`
  names and signatures, the four error types, the `rule_id`/`device_id` keyword,
  the exit-code mapping, every message string) is unchanged. Every pre-existing
  rule-pack and ledger assertion passed **unmodified**; the only test change is
  the additive `test_missing_pack_precedes_empty_array` plus its fixture. No
  `.ambr` snapshot drifted; `--snapshot-update` was never run.
- `tests/test_loaderkit_parse.py` pins the skeleton against a test-local
  third-family binding (a `_Thing` with no extra top-level field), including the
  head/tail seam-independence pins that prove head faults strictly precede tail
  faults — the structural property that buys the rule pack's
  `pack`-before-`entries` precedence. The neutral leaf holds: the package-wide
  import-direction guard's `[parse.py]` case passes and a focused AST pin asserts
  the module imports no pack domain.
- `make all` is green at every work-item HEAD (1563 passed, 1 skipped);
  `interrogate` reports 100%; `make markdownlint` and `make nixie` are clean for
  the touched guide and this ExecPlan.

Deviations from the plan, with rationale:

- **`@overload` → bounded `TypeVar`.** The plan specified `build_entries`'s
  `entry_id` default via `@overload` (a `_HasId`-bound overload plus an
  unbounded one). Three project gates make overloads unworkable here: the repo
  bans `from typing import overload` (Ruff TID), `interrogate` 1.7.0 does not
  recognize the aliased `@typ.overload` decorator (and the codebase mandates
  `import typing as typ`), and Ruff D418 forbids a docstring on an overload
  stub — so interrogate and D418 deadlock. The resolution bounds the entry
  `TypeVar` directly (`build_entries[T: _HasId]`) against a module-local `_HasId`
  `Protocol`, so the default `_entry_id` (which reads `.id`) type-checks while a
  family may still supply its own `entry_id`. This preserves the planned public
  shape (a configurable `entry_id` defaulting to `.id`), needs no `Any` and no
  interrogate config exemption, and keeps the neutral leaf. All real entries
  (`Rule`/`Device`) and the test third family (`_Thing`) satisfy `_HasId`.
- **`loaderkit/__init__` export pulled forward.** The plan scheduled the
  `__init__` re-export for Work item 4, but Work item 2's rebind imports
  `build_entries`/`resolve_schema_version` from the package root, a hard
  dependency, so the export landed in Work item 2's commit. Work item 4 kept the
  guard confirmation and the developers'-guide update.

## Context and orientation

You are working in the git worktree at
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-2-6` on branch
`roadmap-7-2-6`. Use absolute paths. Do not edit anything outside this worktree.

The package under change is `novel_ralph_skill`, a Python deterministic harness.
The relevant layering (design §3.1, §6; `docs/adr-003-shared-interface-contract.md`):

- `novel_ralph_skill/contract/errors.py` defines `EnvelopeMessagesError`, the
  base every domain error subclasses. It is the bottom of the dependency graph.
- `novel_ralph_skill/loaderkit/` is a *neutral leaf* package depending only on
  `contract` and the standard library. It already owns the schema-agnostic loader
  primitives both pack families share: `coerce.py` (the `CoercionErrors` bundle
  plus `where`/`require*`/`reject_unknown_keys`), `load.py` (`entries`,
  `EntriesMessages`, `compile_pattern`, `reject_duplicate_ids`, `load_toml`),
  `scan.py` (`scan_pattern`, `ScannedChapter`, `LineHit`), and `errors.py`
  (`PackError`, `PackFileError`). **It does not yet own the parse skeleton** —
  that is this task. Neither `rulepack` nor `ledger` may be imported here, ever
  (the package-wide import-direction guard in `tests/test_loaderkit_scan.py`
  enforces this by globbing `loaderkit/*.py`).
- `novel_ralph_skill/rulepack/parse.py` defines `parse_rulepack(raw)` and
  `load_rulepack(path)`, the `_rule(entry, *, index)` builder, the
  `_resolve_basis`/`_resolve_page_words` helpers, the `_PACK_KEYS`/`_RULE_KEYS`
  key sets, and the `_ENTRIES_MESSAGES` binding. `parse_rulepack` rejects unknown
  pack keys, requires `schema_version` (rejecting any value `!=
  RULEPACK_SCHEMA_VERSION`), requires the top-level `pack` string, extracts the
  `rule` array, builds each `Rule`, rejects duplicate ids, and returns
  `RulePack(schema_version=…, pack=…, rules=…)`.
- `novel_ralph_skill/ledger/parse.py` is the structural twin minus the `pack`
  field: `parse_ledger(raw)`, `load_ledger(path)`, the `_device(entry, *, index)`
  builder (delegating to `_rationing_fields` in `ledger/_fields.py`), the
  `_LEDGER_KEYS`/`_DEVICE_KEYS` key sets, the `_ENTRIES_MESSAGES` binding, and
  `DeviceLedger(schema_version=…, devices=…)`.

The two `parse_*` orchestrations, side by side:

        # rulepack/parse.py::parse_rulepack
        _reject_unknown_keys(raw, _PACK_KEYS, rule_id=None)
        schema_version = _require_int(raw, "schema_version", rule_id=None)
        if schema_version != RULEPACK_SCHEMA_VERSION:
            raise RulePackError("unsupported rule-pack schema_version …", rule_id=None)
        pack = _require_str(raw, "pack", rule_id=None)            # <- rule-pack only
        raw_entries = entries(raw, array_key="rule", messages=_ENTRIES_MESSAGES, errors=_ERRORS)
        rules = tuple(_rule(entry, index=index) for index, entry in enumerate(raw_entries))
        reject_duplicate_ids((rule.id for rule in rules), errors=_ERRORS)
        return RulePack(schema_version=schema_version, pack=pack, rules=rules)

        # ledger/parse.py::parse_ledger
        _reject_unknown_keys(raw, _LEDGER_KEYS, device_id=None)
        schema_version = _require_int(raw, "schema_version", device_id=None)
        if schema_version != LEDGER_SCHEMA_VERSION:
            raise LedgerError("unsupported device-ledger schema_version …", device_id=None)
        raw_entries = entries(raw, array_key="device", messages=_ENTRIES_MESSAGES, errors=_ERRORS)
        devices = tuple(_device(entry, index=index) for index, entry in enumerate(raw_entries))
        reject_duplicate_ids((device.id for device in devices), errors=_ERRORS)
        return DeviceLedger(schema_version=schema_version, devices=devices)

Everything except the `pack` read and the final result construction is
identical orchestration that this task lifts into `loaderkit`.

Who consumes the parse boundary (do not break these):

- Re-exports: `rulepack/__init__.py` and `ledger/__init__.py` `__all__` carry
  `parse_*`/`load_*`.
- Callers: `load_*` delegate to `parse_*`; the `desloppify` and ledger command
  bodies call `load_*` and catch the four error types.
- Tests: `tests/test_rulepack_loader.py`, `tests/test_rulepack_schema.py`,
  `tests/test_rulepack_properties.py`, `tests/test_ledger_command.py`,
  `tests/test_ledger_detect.py`, `tests/test_ledger_properties.py`,
  `tests/test_ledger_snapshots.py`, and the cross-command contract snapshots
  exercise `parse_*`/`load_*` and assert on the raised types, `.rule_id`/
  `.device_id`, message strings, and exit codes.

The precedent to mirror is roadmap 7.2.2/7.2.5: the shared *body* lives once in
`loaderkit`, each package keeps a thin named *binding*. The developers' guide
section "The shared loader primitives (`loaderkit`)"
(`docs/developers-guide.md`, ~line 1779) and design §6.1/§6.3 record this;
`docs/execplans/roadmap-7-2-5.md` is the directly preceding consolidation and
the structural template for this plan.

Terms:

- *Validating parse boundary* — the pure `parse_*` function that turns a decoded
  `Mapping` into a validated frozen dataclass, runtime-checking every field and
  converting every fault into the family's content error.
- *Skeleton* — the shared `loaderkit` orchestration body this task introduces,
  parameterized on each family's constant, key set, array key, builder, and
  result products.
- *Binding* — a thin per-package module that adapts a shared `loaderkit` body to
  that package's typed channel, nouns, and types, introduced for coercion by
  7.2.2 and for errors by 7.2.5.

## Plan of work

The work proceeds in four atomic, independently committable, gate-passable work
items. Each ends with `make all` green. Items 2 and 3 are symmetric and could be
done in either order; item 1 must precede both; item 4 is last.

### Stage A — understand and propose (no code changes)

Read, in this order: `novel_ralph_skill/loaderkit/coerce.py` and
`novel_ralph_skill/loaderkit/load.py` (the `CoercionErrors`/`EntriesMessages`
bundle style, the `entries`/`reject_unknown_keys`/`require_int`/
`reject_duplicate_ids` signatures the skeleton will call, and the
`file_error=` callable contract); both current `parse.py` modules (the exact
orchestration, the `pack` read asymmetry, the `_rule`/`_device` `index=`
contract, and the docstrings that cite design §6.1/§6.3 and roadmap 5.1.1/7.1.2);
`novel_ralph_skill/rulepack/schema.py` and `ledger/schema.py` (the
`RulePack`/`DeviceLedger` constructors and the two schema-version constants);
`tests/test_loaderkit_load.py` (the sentinel-bundle and verbatim-prose-pin
idioms to copy) and `tests/test_loaderkit_scan.py` (the package-wide
import-direction guard that globs `loaderkit/*.py`). Go/no-go: confirm the
guard globs the package (it does — `_loaderkit_module_paths` uses
`package_dir.glob("*.py")`), so the new `parse.py` is covered automatically;
confirm `parse_rulepack`/`parse_ledger` raise *only* their content error on every
fault (they do — every branch routes through the bundle), so the skeleton
introduces no new exception path.

### Work item 1 — introduce `loaderkit/parse.py` and pin it (red → green)

Create `novel_ralph_skill/loaderkit/parse.py`. It imports only from
`novel_ralph_skill.loaderkit.coerce` (`CoercionErrors`, `Mapping`,
`reject_unknown_keys`, `require_int`), `novel_ralph_skill.loaderkit.load`
(`EntriesMessages`, `entries`, `reject_duplicate_ids`), and the standard library
(`collections.abc`, `typing`). Define the shared skeleton as a **head/tail pair**
per Decisions D-RESULT-CALLBACK and D-SKELETON-HEAD-TAIL — a single all-in-one
call is **rejected** because it cannot reproduce the rule pack's
`pack`-before-`entries` precedence (see Constraints and the superseded
D-SKELETON-RETURNS-TUPLE):

- **Head — `resolve_schema_version`** (name to settle), signature: `raw:
  Mapping`, `*`, `allowed_keys: frozenset[str]`, `schema_version_constant: int`,
  `unsupported_noun: str` (the hyphenated `"rule-pack"`/`"device-ledger"` noun
  for the version sentence), `errors: CoercionErrors`, returning `int`. It
  performs, in order: `reject_unknown_keys(raw, allowed_keys, errors=errors,
  offending_id=None)`; `schema_version = require_int(raw, "schema_version",
  errors=errors, offending_id=None)`; if `schema_version !=
  schema_version_constant`, raise `errors.content_error(f"unsupported
  {unsupported_noun} schema_version {schema_version}; expected
  {schema_version_constant}", None)`; return `schema_version`.
- **Tail — `build_entries`** (name to settle), generic over a `TypeVar` `T` (the
  entry element type), signature: `raw: Mapping`, `*`, `array_key: str`,
  `entries_messages: EntriesMessages`, `errors: CoercionErrors`, `build_entry:
  Callable[[Mapping, int], T]`, `entry_id: Callable[[T], str] = ...` (default
  `lambda e: e.id`), returning `tuple[T, ...]`. It performs, in order:
  `raw_entries = entries(raw, array_key=array_key, messages=entries_messages,
  errors=errors)`; `built = tuple(build_entry(entry, index) for index, entry in
  enumerate(raw_entries))`; `reject_duplicate_ids((entry_id(e) for e in built),
  errors=errors)` — **the id projection is per-family**, supplied by `entry_id`,
  so the skeleton names no pack attribute; return `built`.
- Carry a module docstring and a function docstring with full numpydoc
  `Parameters`/`Returns`/`Raises` on each. No result bundle class is needed (the
  head returns a bare `int`, the tail a bare tuple), so there is no runtime
  synthesizer concern (Constraints, `interrogate` 100%).

Do **not** import or reference any rule-pack/ledger noun or type here. The
`build_entry` callback receives `(entry, index)` and is the per-family builder;
the skeleton never inspects entry fields. The seam between head and tail is the
point the rule pack reads its `pack` field (Work item 2); the two functions are
deliberately separate so the caller controls what happens at that seam.

Write `tests/test_loaderkit_parse.py` first (it fails until the module exists),
mirroring the sentinel idiom in `tests/test_loaderkit_load.py`. Define a
test-local `_SentinelError(EnvelopeMessagesError)` recording `offending_id`, a
`_bundle(...)` building a `CoercionErrors` for it, and a test-local third-family
binding — a `@dataclass` `_Thing(id=…, value=…)` with **no** extra top-level
field — built by a test-local `_build_thing(entry, index)`. It must pin:

1. A happy path composing **both** halves the way a real binding does:
   `version = resolve_schema_version(raw, …)` then `built = build_entries(raw,
   …, build_entry=_build_thing)` — a valid mapping with the right
   `schema_version`, a two-entry array, and distinct ids returns the resolved
   version (an `int`) and a two-tuple of `_Thing`, proving the head resolves the
   version and the tail orchestrates the entries extraction, the build loop, and
   the duplicate-id pass for an arbitrary third family with **no** pack import.
2. Each fault routes through the bundle as the sentinel content error, verbatim.
   Head faults via `resolve_schema_version`: an unknown top-level key (via
   `reject_unknown_keys`'s message), a missing `schema_version`, and an
   unsupported `schema_version` (pin **both** version sentences verbatim, once
   with `unsupported_noun="rule-pack"` and once with `"device-ledger"` — the
   prose pin that closes the silent-drift hazard the per-family version noun
   creates). Tail faults via `build_entries`: an absent/empty/non-mapping entry
   array (via the `EntriesMessages` strings) and a duplicate id (via
   `reject_duplicate_ids`'s message). Assert the raised type is `_SentinelError`
   and the message is the expected string.
3. The build callback is honoured verbatim: a recording `_build_thing` double
   asserts `build_entries` calls it once per entry in authoring order with the
   right `(entry, index)` pairs and uses its return values verbatim (the
   `line_hit`-callback idiom from `tests/test_loaderkit_scan.py`). A second
   `entry_id` double asserts the duplicate-id pass projects ids via the supplied
   `entry_id`, not a hard-coded `.id`.
4. **Head/tail seam independence** — the pin that proves the split actually buys
   the precedence preservation. Assert that calling `resolve_schema_version`
   alone never touches the `array_key`/entries (e.g. pass a mapping whose entry
   array is absent or malformed but whose `schema_version` is unsupported, and
   assert the head raises the *version* fault, never reaching the array), and
   that `build_entries` alone never inspects `schema_version` or the top-level
   key set (pass a mapping with a bad/extra top-level key but a valid entry array
   and assert `build_entries` builds it without complaint). This proves a caller
   can interleave arbitrary work (the rule pack's `pack` read) at the seam and
   that head faults strictly precede tail faults.
5. A belt-and-braces neutral-leaf assertion: parse `loaderkit/parse.py`'s source
   with `ast` and assert it imports nothing from `novel_ralph_skill.rulepack` or
   `novel_ralph_skill.ledger` (complementing the package-wide glob guard).

These tests pin the skeleton so a third pack family inherits the primitive (the
roadmap Success criterion). Run `uv run pytest tests/test_loaderkit_parse.py`
(red before the module, green after), then `make all`.

Cited: design §6.1/§6.3 (`loaderkit` neutral home, the loader-primitive
consolidation); `docs/adr-003-shared-interface-contract.md` (acyclic layering);
`docs/execplans/roadmap-7-2-5.md` (the binding precedent and D-NO-EXTERNAL-RESEARCH);
AGENTS.md "Testing" (unit tests, property tests where logic branches, 100%
docstrings). Skills: `python-router` → `python-types-and-apis` (the `TypeVar`
generic skeleton signature and `Callable` callback typing),
`python-data-shapes` (the frozen result bundle), `python-testing` (the
sentinel-bundle and verbatim-prose-pin idioms).

### Work item 2 — rebind `rulepack/parse.py` onto the skeleton

Rewrite `parse_rulepack` in `novel_ralph_skill/rulepack/parse.py` so it calls the
shared **head**, then reads `pack` **at the original seam**, then calls the
shared **tail**, and constructs `RulePack` — reproducing the live order
exactly (reject-unknown-keys → require `schema_version` → version check → require
`pack` → `entries` → build → dup-ids):

        schema_version = resolve_schema_version(
            raw,
            allowed_keys=_PACK_KEYS,
            schema_version_constant=RULEPACK_SCHEMA_VERSION,
            unsupported_noun="rule-pack",
            errors=_ERRORS,
        )
        pack = _require_str(raw, "pack", rule_id=None)  # <- read at the seam
        rules = build_entries(
            raw,
            array_key="rule",
            entries_messages=_ENTRIES_MESSAGES,
            errors=_ERRORS,
            build_entry=lambda entry, index: _rule(entry, index=index),
        )
        return RulePack(schema_version=schema_version, pack=pack, rules=rules)

Keep `_rule`, `_resolve_basis`, `_resolve_page_words`, `_PACK_KEYS`,
`_RULE_KEYS`, `_ENTRIES_MESSAGES`, and `load_rulepack` exactly as they are.

**Precedence — the round-1 blocking point.** The `pack` read sits **between** the
head and the tail, i.e. *after* the schema-version resolve but *before* the
entry-array extraction, exactly where the original reads it. This is the whole
reason D-SKELETON-HEAD-TAIL splits the skeleton: a single all-in-one call would
force `pack` to be read either before the version resolve (changing precedence)
or after the whole entries/build/dup-ids tail (also changing precedence). Do
**not** "verify by running the suites" — the suites cannot catch a precedence
inversion here, because **no fixture combines a missing `pack` with a bad `rule`
array** (`missing-pack.toml` has a valid one-rule array; `missing-rule-array.toml`
and `empty-rule-array.toml` have a valid `pack`; the property generators never
drop `pack` while corrupting the array). Reason about the intersection
explicitly: for an input simultaneously missing `pack` and carrying an
absent/empty/non-mapping `rule` array, the head succeeds (the keys and version
are fine), then `_require_str(raw, "pack", …)` raises the missing-`pack`
`RulePackError` *before* `build_entries` is ever reached — identical to the
original. Pin this with a new fixture and test (below) rather than trusting the
green corpus.

Add a regression fixture and test (this is the only test edit in this plan; it
**adds** a case, it does not modify an existing assertion):

- Add `tests/data/rulepacks/missing-pack-and-empty-array.toml`: `schema_version
  = 1`, **no** `pack` key, and an empty `rule` array (`rule = []` or no `[[rule]]`
  tables) — an input that trips both the missing-`pack` and the empty-array
  faults at once.
- Add `tests/test_rulepack_loader.py::test_missing_pack_precedes_empty_array`
  asserting `load_rulepack(_fixture("missing-pack-and-empty-array.toml"))` raises
  `RulePackError` with `rule_id is None` **and** a message naming `'pack'` (the
  missing-`pack` sentence), **not** the empty-`rule`-array sentence — pinning that
  the `pack` read precedes the entry-array extraction. Use the existing
  `_fixture`/`pytest.raises(RulePackError)` idiom (lines 118–144 of that file).
  This guards the precedence the corpus left latent and makes the head/tail seam
  position a tested invariant.

Retune the `parse_rulepack` docstring to cite the shared head/tail skeleton while
keeping the "`RulePackError` is the only exception" guarantee, the
`schema_version`/`pack`/`rule`-array fault wording, and the design citations. No
other call site, the `_coerce` binding, the catch sites, or `__all__` changes.
Run the rule-pack suites explicitly — `uv run pytest
tests/test_rulepack_loader.py tests/test_rulepack_schema.py
tests/test_rulepack_detect.py tests/test_rulepack_properties.py
tests/test_contract_errors.py` — every pre-existing assertion passes unchanged
and the new precedence test passes, then `make all`.

Cited: design §6.1; `docs/adr-003-shared-interface-contract.md`;
`docs/execplans/roadmap-7-2-2.md`/`roadmap-7-2-5.md` (the binding precedent);
`novel_ralph_skill/rulepack/parse.py`. Skills: `python-router` →
`python-errors-and-logging` (preserving the single-exception-type boundary
guarantee and the fault precedence), `python-testing` (the fixture-pinned
precedence regression).

### Work item 3 — rebind `ledger/parse.py` onto the skeleton

The symmetric change for `novel_ralph_skill/ledger/parse.py`: `parse_ledger`
calls the same head then tail back-to-back, **with no interleave**, then
constructs the result:

        schema_version = resolve_schema_version(
            raw,
            allowed_keys=_LEDGER_KEYS,
            schema_version_constant=LEDGER_SCHEMA_VERSION,
            unsupported_noun="device-ledger",
            errors=_ERRORS,
        )
        devices = build_entries(
            raw,
            array_key="device",
            entries_messages=_ENTRIES_MESSAGES,
            errors=_ERRORS,
            build_entry=lambda entry, index: _device(entry, index=index),
        )
        return DeviceLedger(schema_version=schema_version, devices=devices)

The ledger has **no** top-level string field (no `pack` analogue), so there is
nothing to read at the head/tail seam and therefore **no precedence question and
no asymmetry to preserve** — the head and tail run back-to-back, behaviourally
identical to the original single-pass order. This is the explicit asymmetry the
round-1 review's advisory asked the plan to state: the seam exists for the rule
pack's benefit (Work item 2); the ledger simply does not use it. Keep `_device`,
`_DEVICE_KEYS`/`_LEDGER_KEYS`, `_ENTRIES_MESSAGES`, and `load_ledger` as they
are. Retune the `parse_ledger` docstring to cite the shared head/tail skeleton
while keeping the "`LedgerError` is the only exception" guarantee and the
citations. No call site, the `_coerce`/`_fields` bindings, catch sites,
`__all__`, or test changes. Run the ledger suites — `uv run pytest
tests/test_ledger_command.py tests/test_ledger_detect.py
tests/test_ledger_properties.py tests/test_ledger_snapshots.py` — unchanged, then
`make all`.

Cited: design §6.3; `docs/adr-003-shared-interface-contract.md`;
`novel_ralph_skill/ledger/parse.py`. Skills: `python-router` →
`python-errors-and-logging`, `python-testing`.

### Work item 4 — export, guard, and document

- In `novel_ralph_skill/loaderkit/__init__.py`, export **both** skeleton
  functions (`resolve_schema_version` and `build_entries`, names as settled in
  Work item 1) from `loaderkit.parse` and add them to `__all__` (alphabetically,
  matching the existing list style), so the shared head/tail skeleton is a
  first-class set of `loaderkit` primitives beside `CoercionErrors`,
  `EntriesMessages`, and `PackError`.
- Confirm the package-wide import-direction guard
  (`tests/test_loaderkit_scan.py::test_loaderkit_module_imports_no_pack_domain`)
  now exercises `loaderkit/parse.py`. It globs `loaderkit/*.py`, so it should
  pick the new module up automatically; the focused `ast` assertion added in Work
  item 1 is the belt-and-braces pin. If the glob does not cover it, escalate (it
  is expected to).
- Update the developers' guide section "The shared loader primitives
  (`loaderkit`)" (`docs/developers-guide.md`, ~line 1779): add the parse skeleton
  to the list of primitives `loaderkit` now owns and record that each package
  binds it — supplying its constant, key set, array key, builder, and result
  construction — mirroring the coercion and error bindings, with the rule pack's
  extra `pack` read staying at its call site. This is a docs change, so
  additionally run `make markdownlint` and `make nixie`.

Cited: design §6.1/§6.3; `docs/adr-003-shared-interface-contract.md`;
AGENTS.md (documentation update obligation); `docs/developers-guide.md`. Skills:
`en-gb-oxendict` (Oxford spelling in the guide prose).

### Stage D — hardening

After item 4, run the full `make all` once more, plus `make markdownlint` and
`make nixie` for the touched markdown. Confirm no snapshot drift and no
`interrogate` shortfall. Update Progress, Surprises, and Outcomes.

## Concrete steps

Run all commands from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-2-6`.

1. Work item 1 — create the module and its test, confirm red then green:

        uv run pytest tests/test_loaderkit_parse.py
        # before the module exists: collection/import error or failures
        # after writing loaderkit/parse.py: N passed
        make all

   Expected tail of `make all`: all suites pass; `interrogate` reports 100%;
   Ruff and `ty` clean.

2. Work item 2 — rebind rulepack (read `pack` at the head/tail seam), add the
   precedence fixture and test, then:

        uv run pytest tests/test_rulepack_loader.py tests/test_rulepack_schema.py \
          tests/test_rulepack_detect.py tests/test_rulepack_properties.py \
          tests/test_contract_errors.py
        make all

   Expected: every pre-existing assertion passes unchanged; the **added**
   `test_missing_pack_precedes_empty_array` passes (the only test edit is this
   addition — no existing assertion is modified); no `.ambr` snapshot diff.

3. Work item 3 — rebind ledger, then:

        uv run pytest tests/test_ledger_command.py tests/test_ledger_detect.py \
          tests/test_ledger_properties.py tests/test_ledger_snapshots.py
        make all

   Expected: passes unchanged; no `.ambr` snapshot diff.

4. Work item 4 — export, guard, document, then:

        make all
        make markdownlint
        make nixie

Format only the files you changed before each commit: run the markdown formatter
on the specific docs path you touched (`mdtablefix docs/developers-guide.md
docs/execplans/roadmap-7-2-6.md` then `markdownlint-cli2 --fix
docs/developers-guide.md docs/execplans/roadmap-7-2-6.md`) and `make
markdownlint`/`make nixie`; do **not** run a repo-global format that churns
unrelated files. Commit after each work item with a gated commit.

## Validation and acceptance

Acceptance is behavioural and observable:

- **Single home.** `novel_ralph_skill/loaderkit/parse.py` exists and owns the
  schema-version resolve-and-reject block (the head), the entry-array extraction
  call, the per-entry build loop, and the duplicate-id rejection (the tail); `git
  grep -n "schema_version !=" novel_ralph_skill/rulepack/parse.py
  novel_ralph_skill/ledger/parse.py` returns nothing (the comparison now lives
  only in the head), and each `parse_*` is a thin head→(seam)→tail call into the
  skeleton plus its per-family result construction.
- **Precedence preserved.** The rule pack reads `pack` at the head/tail seam, so
  `parse_rulepack`'s live fault order (… → version check → require `pack` →
  `entries` → …) is byte-identical; the new
  `test_missing_pack_precedes_empty_array` passes, pinning that a simultaneously
  missing-`pack` + empty-array input still raises the missing-`pack` fault. The
  ledger has no seam interleave and no precedence change.
- **No regressions.** `make all` is green. The new test
  `tests/test_loaderkit_parse.py` fails before `loaderkit/parse.py` exists and
  passes after. Every pre-existing rule-pack and ledger assertion passes
  **unmodified** (the only test change is the *additive*
  `test_missing_pack_precedes_empty_array` plus its fixture), proving the public
  surface (the `parse_*`/`load_*` names and signatures, the four error types, the
  `rule_id`/`device_id` keyword and attribute, the exit-code mapping via the catch
  sites, every message string) is unchanged.
- **No snapshot drift.** No `.ambr` file changes; `--snapshot-update` was not
  run.
- **Neutral leaf preserved.** The package-wide `loaderkit` import-direction guard
  passes with `parse.py` in scope; `loaderkit.parse` imports no pack symbol (the
  focused `ast` pin in `tests/test_loaderkit_parse.py` plus the package glob).
- **Documented single source of truth.** The developers' guide records the parse
  skeleton as a `loaderkit`-owned primitive each package binds.

Quality criteria ("done"):

- Tests: `make test` green; `tests/test_loaderkit_parse.py` is the new pin; all
  rulepack/ledger/contract suites green unchanged.
- Lint/typecheck: `make lint` (Ruff + `interrogate` 100% + Pylint) and `make
  typecheck` (`ty`) clean.
- Markdown: `make markdownlint` and `make nixie` clean for the touched guide and
  this ExecPlan.

Quality method: `make all` for code; `make markdownlint` + `make nixie` for
markdown. No new dependency, no behaviour change.

## Idempotence and recovery

Each work item is a self-contained edit ending in a gated commit, so the tree is
clean between items and any item can be re-run from a clean checkout. If `make
all` fails mid-item, the failure is local to that item's edit; revert the
working-tree change for that file and re-apply. If a commit must be parked for
formatter churn, name the stash `df12-stash v1 task=roadmap-7-2-6 kind=discard
reason="formatter churn"`. No destructive or irreversible step is involved.

## Artefacts and notes

The two near-copy orchestrations being consolidated are shown in full in
*Context and orientation* above. The neutral products the skeleton returns (the
resolved `schema_version` int and the built entry tuple) are constructed into
`RulePack`/`DeviceLedger` at each call site; the rule pack additionally reads its
top-level `pack` string there.

The `CoercionErrors` and `EntriesMessages` bundles the skeleton receives
(`novel_ralph_skill/loaderkit/coerce.py`, `load.py`) are unchanged; the skeleton
calls the existing `reject_unknown_keys`, `require_int`, `entries`, and
`reject_duplicate_ids` primitives, adding only the orchestration that sequences
them.

## Interfaces and dependencies

At the end of the work the following must exist.

In `novel_ralph_skill/loaderkit/parse.py` (names to settle in implementation;
shape fixed by D-RESULT-CALLBACK / D-SKELETON-HEAD-TAIL — a head/tail pair, **not**
the superseded single `parse_pack` call):

        from novel_ralph_skill.loaderkit.coerce import CoercionErrors, Mapping
        from novel_ralph_skill.loaderkit.load import EntriesMessages


        def resolve_schema_version(
            raw: Mapping,
            *,
            allowed_keys: frozenset[str],
            schema_version_constant: int,
            unsupported_noun: str,
            errors: CoercionErrors,
        ) -> int: ...


        def build_entries[T](
            raw: Mapping,
            *,
            array_key: str,
            entries_messages: EntriesMessages,
            errors: CoercionErrors,
            build_entry: cabc.Callable[[Mapping, int], T],
            entry_id: cabc.Callable[[T], str] = ...,
        ) -> tuple[T, ...]: ...

In `novel_ralph_skill/rulepack/parse.py` (`parse_rulepack` signature unchanged):

        def parse_rulepack(raw: cabc.Mapping[str, object]) -> RulePack: ...

In `novel_ralph_skill/ledger/parse.py` (`parse_ledger` signature unchanged):

        def parse_ledger(raw: cabc.Mapping[str, object]) -> DeviceLedger: ...

`novel_ralph_skill/loaderkit/__init__.py` re-exports the skeleton in `__all__`.
No external dependencies are added; the only imports are
`novel_ralph_skill.loaderkit` siblings, `novel_ralph_skill.contract.errors`
(transitively, via the bundle type hints), and the standard library.

## Addenda

Small, surgical corrections folded onto this completed task after its reviews and
audits. Each runs as a no-plan, no-review lightweight pass and is mirrored by a
nested sub-task on the roadmap under 7.2.6.

- 7.2.6.1 — Replace the `PLR0913` skeleton suppressions with a per-family spec
  bundle (from review:7.2.6; low). `resolve_schema_version` and `build_entries`
  each carry a paired `noqa: PLR0913` plus `pylint: disable` for their keyword
  parameters. Fold the per-family parameters into a small frozen dataclass so both
  suppressions retire and a future third family fills one bundle rather than five
  loose kwargs. Tidiness/altitude only; current behaviour is correct.
- 7.2.6.2 — Pin the `build_entries` enumerate-build-dedup loop with a Hypothesis
  property (from review:7.2.6; low). The `build_entries` tail is currently pinned
  only by example-based tests. Add a Hypothesis strategy generating arrays of N
  entries with controlled id collisions and authoring orders to harden the
  authoring-order and first-duplicate-wins guarantees against future edits,
  matching the property-test discipline AGENTS.md asks for where logic branches.
- 7.2.6.3 — Bring device-ledger parse-boundary test coverage to rule-pack parity
  over the shared skeleton (from audit:7.2.6; medium). After this task both pack
  families share `resolve_schema_version`/`build_entries`, but only the rule pack
  exercises the head/tail faults (unsupported/non-integer `schema_version`,
  unknown keys, empty/missing entry array) end-to-end against fixtures. The ledger
  binding has neither fixtures nor tests, so a mis-wired `unsupported_noun`, key
  set, or array key in `parse_ledger` would pass the whole ledger suite green. Add
  the missing ledger fixtures and a `tests/test_ledger_loader.py` mirroring
  `tests/test_rulepack_loader.py`, pinning `unsupported device-ledger
  schema_version N; expected 1` verbatim.
