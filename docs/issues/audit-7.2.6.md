# Post-merge audit — roadmap task 7.2.6

Task 7.2.6 retired the final un-consolidated loader primitive: the *validating
parse boundary* itself (commit `3ef7478`). Both `parse_rulepack` and
`parse_ledger` carried a structurally identical orchestration — reject an unknown
top-level key, resolve and reject an unsupported `schema_version`, extract the
non-empty entry array, build one validated entry per element in authoring order,
reject duplicate ids — that `loaderkit/parse.py` now owns as a **head/tail pair**.
The head, `resolve_schema_version`, rejects unknown keys and resolves the version;
the tail, `build_entries`, extracts the array, builds each entry through a
caller-supplied builder, and rejects duplicate ids over a caller-supplied
`entry_id` projection. The skeleton returns only neutral products (the resolved
version int and the built entry tuple), so each package constructs its own
`RulePack`/`DeviceLedger` at the leaf and `loaderkit` imports no pack result type.
The split into two functions preserves the rule pack's live
`pack`-before-`entries` fault precedence by letting it read `pack` at the head/tail
seam. The change adds `tests/test_loaderkit_parse.py` and documents the skeleton
in the developers' guide. It closes the loaderkit-consolidation lineage (7.2.2
coercion/scan bodies, 7.2.3 scan shapes, 7.2.5 error hierarchies) for the
validating-parse leg.

This audit reviews the merged state at `origin/main` (commit `3ef7478`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-segregation issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a location and a concrete proposed fix.

The 7.2.6 change itself is in excellent shape. `loaderkit/parse.py` is a neutral
leaf — its no-pack-domain invariant is pinned directly by
`test_parse_module_imports_no_pack_domain` as well as the package-wide glob guard;
the head/tail split is justified by a documented decision (`D-SKELETON-HEAD-TAIL`)
and the seam independence that buys the rule pack's precedence is pinned by
`test_head_raises_version_fault_without_reaching_array` and
`test_tail_builds_without_inspecting_top_level_keys_or_version`; the result-callback
neutrality (`D-RESULT-CALLBACK`) is sound; and the module, both rebound `parse_*`
docstrings, and the developers'-guide section are precise. The material findings
below are residual seams the consolidation surfaced rather than faults in the
merged change, plus a test-coverage asymmetry the shared boundary now makes
salient. None is tracked by an existing roadmap task (verified against the open
phase-7.2/7.3 single-source steps).

## 1. The ledger family does not exercise the shared skeleton head end-to-end

- **Category:** test-gap
- **Severity:** medium
- **Location:** `tests/test_ledger_command.py:44-48` (`_BAD_LEDGER_FIXTURES`) and
  `tests/data/ledgers/` (seven fixtures); contrast `tests/data/rulepacks/`
  (twenty-two fixtures, including `bad-version.toml`,
  `non-integer-schema-version.toml`, `unknown-pack-key.toml`,
  `unknown-rule-key.toml`, `empty-rule-array.toml`, `missing-rule-array.toml`) and
  the assertions in `tests/test_rulepack_loader.py:79-82,121,172-175`.

After 7.2.6 both families route their top-level orchestration through the same
`resolve_schema_version`/`build_entries` skeleton, parameterised only by their
constant, key set, array key, and the per-family `unsupported_noun`
(`"rule-pack"`/`"device-ledger"`). The rule pack exercises every head/tail fault
end-to-end against real fixtures — an unsupported `schema_version`, a non-integer
`schema_version`, an unknown top-level key, an unknown entry key, an empty entry
array, and a missing entry array — but the ledger's bad-fixture set covers only
the *entry-body* faults (`no-ration`, `two-windows`, `bad-pattern`,
`duplicate-id`, `non-positive-max-count`). There is no ledger fixture or test for
an unsupported `device-ledger` `schema_version`, a non-integer `schema_version`,
an unknown `[ledger]`/`[[device]]` key, an empty `device` array, or a missing
`device` array. `tests/test_loaderkit_parse.py` pins both `unsupported_noun`
sentences verbatim, but only in isolation against a synthetic `_Thing` binding;
no test proves `parse_ledger` passes `unsupported_noun="device-ledger"` (or
its `_LEDGER_KEYS`/`"device"` array key) into the skeleton. A future edit that
swapped the ledger's `unsupported_noun`, dropped a key from `_LEDGER_KEYS`, or
mis-wired the array key would pass the whole ledger suite green.

- **Proposed fix:** Add the missing ledger fixtures mirroring the rule pack's
  set — `bad-version.toml`, `non-integer-schema-version.toml`,
  `unknown-ledger-key.toml`, `unknown-device-key.toml`, `empty-device-array.toml`,
  `missing-device-array.toml` — and extend `_BAD_LEDGER_FIXTURES` (or add direct
  `parse_ledger` unit assertions in a `tests/test_ledger_loader.py` mirroring
  `tests/test_rulepack_loader.py`) so each exits 2 and pins the family-specific
  sentence verbatim, in particular `"unsupported device-ledger schema_version N;
  expected 1"`. This both closes the parity gap and pins the ledger's skeleton
  wiring at the family level rather than only generically.

## 2. `build_entries` (and `scan_pattern`) force every caller to wrap a keyword-only builder in an identity lambda

- **Category:** ergonomics
- **Severity:** low
- **Location:** `novel_ralph_skill/loaderkit/parse.py:206` (the positional
  `build_entry(entry, index)` call); `novel_ralph_skill/rulepack/parse.py:279`
  and `novel_ralph_skill/ledger/parse.py:194` (the
  `lambda entry, index: _rule(entry, index=index)` /
  `lambda entry, index: _device(entry, index=index)` wrappers).

`build_entries` calls its builder positionally — `build_entry(entry, index)` —
but both real builders (`_rule`, `_device`) take `index` as a keyword-only
argument (`def _rule(entry, *, index)`), so neither can be passed directly. Each
call site interposes an identity lambda whose sole purpose is to translate the
positional `index` into the keyword form. The two lambdas are byte-identical bar
the function name, and a third family would write a third copy. This is the same
shape as the already-recorded `scan_pattern` `line_hit` identity-lambda seam
(`docs/issues/audit-7.2.5.md` Finding 4), now repeated at the parse boundary.

- **Proposed fix:** Make `build_entries`'s `build_entry` parameter accept the
  builder by its natural signature — either type it
  `Callable[[Mapping, int], T]` and call it positionally while changing `_rule`/
  `_device` to take a positional `index` (`def _rule(entry, index)`), or document
  the call convention as keyword (`build_entry(entry, index=index)`) and let the
  builders keep their keyword-only `index`. Either removes both identity lambdas
  and the cloned third copy a future family would add. If the indirection is
  retained deliberately, note in the docstring why the wrapper cannot be elided.

## 3. The two `_coerce.py` binding shims are near-identical trivial-forwarder modules

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/rulepack/_coerce.py` and
  `novel_ralph_skill/ledger/_coerce.py` (the `_where`, `_reject_unknown_keys`,
  `_require_str`, `_require_int`, and — ledger only — `_require` forwarders).

The 7.2.2/7.2.5/7.2.6 lineage consolidated every coercion *body*, but each family
still carries a hand-written shim whose only job is to rename the shared
`offending_id=` keyword to a family-specific one (`rule_id=` / `device_id=`) and
re-bind the noun pair. The two shims are structurally identical line-for-line
forwarders differing only in that keyword name, the bound `CoercionErrors` nouns,
and the docstring prose; a third pack family clones a third ~70-line shim of
trivial one-line wrappers. The keyword rename is the entire differentiator — the
bodies are otherwise the shared `loaderkit.coerce` functions called with the same
arguments.

- **Proposed fix:** Eliminate the per-family keyword rename so the shim collapses
  to data, not code. Either (a) standardise `parse.py`/`_fields.py` call sites on
  the shared `offending_id=` keyword and import the `loaderkit.coerce` helpers
  directly with the family's `_ERRORS` bundle bound via `functools.partial`,
  reducing each `_coerce.py` to the single `CoercionErrors` construction plus the
  re-exported `Mapping` alias; or (b) if the family-specific keyword is considered
  worth preserving for readability at call sites, generate the forwarders from a
  single shared factory (`bind_coercion(errors, id_keyword="rule_id")`) so the
  forwarder bodies live in one place and a third family supplies one call rather
  than a third file.

## 4. The two `_coerce.py` shims expose divergent forwarder surfaces

- **Category:** inconsistency
- **Severity:** low
- **Location:** `novel_ralph_skill/ledger/_coerce.py:58-60` (exports a `_require`
  forwarder) versus `novel_ralph_skill/rulepack/_coerce.py` (does not).

The ledger shim re-exports a `_require` forwarder (consumed by
`ledger/_fields.py:_allowed_chapters`) while the rule-pack shim does not, because
the rule pack happens never to need the bare `require`. The two shims are
presented throughout the docstrings and the developers' guide as the same
"thin binding" pattern, yet their public-to-the-package surfaces differ by one
forwarder with no documented reason. A reader comparing the two as parallels has
to notice the asymmetry and infer it is incidental rather than meaningful.

- **Proposed fix:** Fold this into Finding 3's resolution: if the shims are
  generated from a shared factory the forwarder set is uniform by construction.
  If the hand-written shims are kept, either add the `_require` forwarder to the
  rule-pack shim for surface parity (and note it is unused there) or add a one-line
  comment in `ledger/_coerce.py` explaining that `_require` is present only because
  `_fields.py` needs the bare value for the `allowed_chapters` array check, so the
  asymmetry reads as intentional.

## 5. `make markdownlint`/`make nixie` are still not folded into the `make all` gate

- **Category:** docs-gap
- **Severity:** low
- **Location:** `Makefile` (the `all:` prerequisites versus the standalone
  `markdownlint:` and `nixie:` targets).

The recurring standing gap, re-noted because 7.2.6's developers'-guide touch (the
new loaderkit validating-parse-skeleton section) again relied on manual Markdown
linting rather than an enforced gate; this audit runs both by hand. Same item as
`docs/issues/audit-6.3.3.md` Finding 5 and `audit-7.2.5.md` Finding 5.

- **Proposed fix:** Defer to the existing roadmap handling of this recurring item
  if one exists; otherwise fold `markdownlint nixie` into `make all` (or add a
  docs-lint CI job) so a docs-only change cannot merge without both Markdown gates
  running.
