# Post-merge audit — roadmap task 7.2.5

Task 7.2.5 consolidated the parallel rule-pack and device-ledger error
hierarchies behind one shared `loaderkit.errors` factory (commit `29655f3`). It
introduced two neutral base classes — `PackError` (the exit-`2` content base)
and `PackFileError` (the exit-`3` file base), each a distinct
`EnvelopeMessagesError` subclass — and rebound `RulePackError`/`RulePackFileError`
and `LedgerError`/`LedgerFileError` onto them, retiring the structurally
identical two-class hierarchies that differed only in the id-attribute name
(`rule_id`/`device_id`) and the nouns. It exported the bases from `loaderkit`,
documented them in the developers' guide, and added `tests/test_loaderkit_errors.py`.
It closes the loaderkit-consolidation lineage (7.2.2 coercion/scan bodies, 7.2.3
scan shapes, 7.2.4 scan-shape stragglers) for the error-channel leg.

This audit reviews the merged state at `origin/main` (commit `29655f3`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-segregation issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a location and a concrete proposed fix.

The 7.2.5 change itself is in excellent shape. The `loaderkit.errors` module is
a neutral leaf (its import-direction invariant is pinned by
`test_errors_module_imports_no_pack_domain`), the two bases are correctly kept as
distinct siblings so the exit-`2` and exit-`3` catch channels stay separable, the
`D-BASE-MIXIN` decision to keep literal `class` statements preserves
`interrogate` docstring coverage and Sphinx cross-references, and the developers'
guide and module docstrings are precise. The material findings are not faults in
the merged change but residual near-copies the loaderkit lineage has *not yet*
reached — the per-pack `parse.py` orchestration bodies and the `_coerce.py`
binding shims — plus a test-coverage gap in the very binding 7.2.5 introduced and
a now-obsolete callback seam the relocation lineage left behind. None of these
findings is tracked by an existing roadmap task (verified against the phase-7.2
and phase-7.3 single-source steps and the open 7.3.9/8.1.x tasks).

## 1. The real `*Error` bindings to the `loaderkit` bases are unguarded by any test

- **Category:** test-gap
- **Severity:** medium
- **Location:** `novel_ralph_skill/rulepack/errors.py:39,68` and
  `novel_ralph_skill/ledger/errors.py:41,71` (the `RulePackError(PackError)`,
  `RulePackFileError(PackFileError)`, `LedgerError(PackError)`,
  `LedgerFileError(PackFileError)` bindings); no covering assertion in
  `tests/test_loaderkit_errors.py`, `tests/test_rulepack_schema.py`, or
  `tests/test_ledger_schema.py`.

The central invariant 7.2.5 introduces — that the *real* pack error classes bind
the shared `loaderkit` bases rather than carrying their own near-identical
hierarchies — is asserted nowhere. `tests/test_loaderkit_errors.py` pins the
bases only against *test-local* synthetic subclasses (`_SampleError`,
`_SampleFileError` with an arbitrary `sample_id` keyword), and
`tests/test_rulepack_schema.py:124-126` asserts only that `RulePackError` and
`RulePackFileError` are not subclasses *of each other*. No test asserts
`issubclass(RulePackError, PackError)`, `issubclass(RulePackFileError,
PackFileError)`, `issubclass(LedgerError, PackError)`, or
`issubclass(LedgerFileError, PackFileError)`. The roadmap success criterion for
7.2.5 is that "the rule-pack and ledger packages bind it rather than carrying
near-identical copies … a test pins the factory so a third pack family inherits
the primitive instead of cloning a third copy", but the only test added pins the
*synthetic* third family, not the two *actual* bindings. A future edit that
re-detaches `RulePackError` from `PackError` (re-cloning the body, the exact
near-copy 7.2.5 retired) would leave the entire suite green — the developers'
guide even describes the test as pinning the bases "against a test-local
third-family id keyword", confirming the real bindings are documented but
untested.

- **Proposed fix:** Add a small parametrized test (in
  `tests/test_loaderkit_errors.py`, or a new
  `tests/test_pack_errors_bind_loaderkit_bases.py`) that imports the four real
  classes and asserts `issubclass(RulePackError, PackError)`,
  `issubclass(LedgerError, PackError)`, `issubclass(RulePackFileError,
  PackFileError)`, and `issubclass(LedgerFileError, PackFileError)`, plus the
  cross-negative (`not issubclass(RulePackError, PackFileError)`, etc.) so the
  content/file channel split is pinned for the concrete classes too. This guards
  the consolidation's load-bearing invariant against a silent re-fork, exactly as
  `test_loaderkit_scan.py`'s AST guard pins the relocated scan shapes' single
  home.

## 2. The two `parse.py` validating boundaries are near-identical structural copies

- **Category:** similarity
- **Severity:** medium
- **Location:** `novel_ralph_skill/rulepack/parse.py` (`parse_rulepack`,
  `_rule`, `load_rulepack`) versus `novel_ralph_skill/ledger/parse.py`
  (`parse_ledger`, `_device`, `load_ledger`).

The loaderkit lineage consolidated the shared *primitives* (coercion, entries,
pattern-compile, duplicate-id, file-load, scan, and now the error hierarchy) but
left each pack's `parse.py` *orchestration* as a parallel near-copy. The three
function pairs run the same skeleton with only noun and schema-constant
substitutions:

- `parse_rulepack`/`parse_ledger`: reject unknown top-level keys → `_require_int`
  the `schema_version` → compare it to the pack's `*_SCHEMA_VERSION` and raise the
  pack's content error on mismatch → `entries(...)` the array → build each entry
  in authoring order → `reject_duplicate_ids(...)`. The `schema_version`
  validation block (`parse.py:253-259` / `parse.py:173-179`) is structurally
  identical, differing only in `RULEPACK_SCHEMA_VERSION`/`LEDGER_SCHEMA_VERSION`,
  the noun, and the error type.
- `_rule`/`_device`: the `if "id" not in entry or not isinstance(entry["id"],
  str): raise … at index {index}` guard (`parse.py:189-191` / `parse.py:112-114`)
  is byte-identical bar the noun and error type; both then `_reject_unknown_keys`,
  `_require_str` the pattern, and construct the frozen schema type with
  `compile_pattern(pattern, errors=_ERRORS, offending_id=…)`.
- `load_rulepack`/`load_ledger`: both are a two-line `load_toml(...)` →
  `parse_*(raw)` convenience differing only in the `noun=` and `file_error=`
  arguments.

A future change to the boundary contract (a new `schema_version` policy, a change
to the id-missing message, a different array-coercion rule) must be applied to
both with no guard they stay in step — the same drift class the loaderkit
consolidation was created to close, one layer up. This is the orchestration twin
of the 7.2.2 coercion-body consolidation, and it is *not* covered by any existing
roadmap task (7.2.x consolidated only the primitives; 7.3.9 targets the
*command-body* desloppify/ledger pipeline, not the loader `parse.py`).

- **Proposed fix:** Lift the shared boundary skeleton into a `loaderkit` helper
  parameterized on the per-pack substitutions — the `entries` messages, the
  `CoercionErrors` bundle, the expected `schema_version` constant and its key
  vocabularies, the id-missing message template, and an entry-builder callback —
  so each pack supplies only those. At minimum, extract the identical
  `schema_version` validation block and the id-missing guard into shared
  `loaderkit` helpers (`require_schema_version(raw, *, expected, errors)` and an
  id-resolution helper) that both `parse.py` boundaries call, retiring the
  largest verbatim spans while leaving the pack-specific field logic in place.

## 3. The two `_coerce.py` binding shims are parallel near-copies

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/rulepack/_coerce.py` versus
  `novel_ralph_skill/ledger/_coerce.py`.

Post-7.2.2 both `_coerce.py` modules are thin bindings of the shared
`loaderkit.coerce` primitives, but the binding *boilerplate* itself is a
near-copy: each builds a `CoercionErrors` bundle with a
`content_error=lambda msg, <id>: <Error>(msg, <id>=<id>)` and the pack's noun
pair, re-exports `type _Mapping = Mapping`, and defines one-line `_where`,
`_reject_unknown_keys`, `_require_str`, `_require_int` (and, in the ledger,
`_require`) forwarders that differ only in the id keyword name (`rule_id` versus
`device_id`) and the bound `_ERRORS`. The forwarders exist purely to rename the
`offending_id=` keyword to the package's public `<thing>_id=` spelling so the
`parse.py` call sites need not change — a deliberate seam, but one duplicated per
pack and growing per-pack-family by a fixed block of forwarders rather than a
single binding line.

- **Proposed fix:** This is lower-priority than Findings 1-2 and is partly a
  consequence of the keyword-rename seam being a per-pack convenience. If Finding
  2's boundary consolidation lands, route the shared boundary through the
  `CoercionErrors` bundle directly (passing `offending_id=` rather than the
  renamed `<thing>_id=`), which removes the need for most forwarders and collapses
  each `_coerce.py` to its one bundle definition plus the `_where` convenience.
  Alternatively, provide a `loaderkit.coerce.bind(errors)` factory that returns
  the bound forwarder set, so a pack writes one `bind(_ERRORS)` call rather than
  re-spelling five forwarders. Treat as a follow-on to whichever boundary
  consolidation Finding 2 chooses.

## 4. The `line_hit` callback seam is now obsolete and its lambda is duplicated verbatim

- **Category:** ergonomics
- **Severity:** low
- **Location:** `novel_ralph_skill/loaderkit/scan.py:66-92` (the `line_hit`
  parameter) and its two verbatim call sites
  `novel_ralph_skill/rulepack/detect.py:207` and
  `novel_ralph_skill/ledger/detect.py:245`.

`scan_pattern` takes a `line_hit: Callable[[int, int], LineHit]` constructor, and
both detectors pass the identical `lambda chapter, line: LineHit(chapter=chapter,
line=line)`. The seam's documented justification was historical: before 7.2.3
relocated `LineHit` into `loaderkit.scan`, the callback "kept the shared body free
of any `Rule`/`Device` knowledge" by not naming a pack-domain hit type. Since
7.2.3, `LineHit` lives in `scan.py` itself, so `scan_pattern` could construct
`LineHit(chapter=…, line=…)` directly — the callback now injects a type the
module already owns, and the two call sites pass a verbatim identity lambda whose
only effect is to re-supply that owned constructor. (Roadmap 7.2.3.2 retuned the
*docstring* framing away from the obsolete "pack-domain hit type" wording, but the
*seam itself* survived; 7.2.3 added a callback-contract test that would need to
move with it.)

- **Proposed fix:** Drop the `line_hit` parameter from `scan_pattern` and
  construct `LineHit(chapter=chapter.number, line=index)` inline in the shared
  body, deleting the duplicated lambda from both detectors. Repoint the
  `line_hit`-callback contract test (added in 7.2.3) at the direct-construction
  behaviour. If the callback is deliberately retained as a future extension seam
  (a third family wanting a richer hit type), record that intent in the docstring
  and default the parameter to the `LineHit` constructor so the two call sites
  stop re-passing the identity lambda.

## 5. `make markdownlint`/`make nixie` are not folded into the `make all` gate

- **Category:** test-gap
- **Severity:** low
- **Location:** `Makefile` (`all:` prerequisites versus the `markdownlint` and
  `nixie` targets); `.github/workflows/`.

The `Makefile`'s `all` target chains the code gates but the `markdownlint` and
`nixie` targets sit outside that chain, so a docs-only change — for instance a
developers'-guide edit like the one 7.2.5 carried — can merge without either
Markdown gate running automatically; this audit runs them by hand. This is the
same standing gap recorded in `docs/issues/audit-6.3.3.md` Finding 5 and is
re-noted here only to register that 7.2.5's docs touch (the developers'-guide
loaderkit-error section) again relied on manual Markdown linting rather than an
enforced gate. Defer to the existing roadmap handling of that recurring item if
one exists; otherwise fold `markdownlint nixie` into `make all` or add a
docs-lint CI job.
