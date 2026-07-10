# Post-merge audit — roadmap task 7.2.7

Task 7.2.7 retired the two builder-seam identity lambdas and collapsed the
per-family `_coerce.py` forwarder shims (commit `6d28cbc`). It introduced a
shared `bind_coercion` factory in `loaderkit/coerce.py` that returns a frozen
`BoundCoercion` bundle exposing every coercion helper pre-bound to one family's
`CoercionErrors`, so each family's `_coerce.py` is now a single `bind_coercion`
call rather than a hand-written set of `_where`/`_require*`/`_reject_unknown_keys`
forwarders. In parallel it changed the two parameterized seams in
`loaderkit/parse.py` and `loaderkit/scan.py` to a keyword-call convention
(`build_entry(entry, index=index)` and `line_hit(chapter=…, line=…)`) so the
keyword-only `_rule`/`_device` builders and the `kw_only` `LineHit` class bind
directly — `build_entry=_rule`, `line_hit=LineHit` — retiring the byte-identical
identity lambdas at both detector and both parser call sites.

This change directly closes Findings 2, 3, and 4 of `docs/issues/audit-7.2.6.md`
(the identity-lambda seam, the near-identical forwarder shims, and their divergent
surfaces). The closure is clean: both `_coerce.py` modules are now a single
`bind_coercion` call with a uniform surface, and a third pack family adds one
binding rather than a third forwarder file. The new behaviour is well tested —
`tests/test_loaderkit_coerce.py` pins the bundle against a synthetic third-family
`_ThingError` binding (proving the keyword rename lives inside `content_error` and
the bundle hides it), `tests/test_coerce_binding_wiring.py` drives the repointed
`_fields.py`/`parse.py` sites end-to-end through the real loaders, and the
`recording_build`/`recording_line_hit` doubles in `test_loaderkit_parse.py` and
`test_loaderkit_scan.py` now declare keyword-only parameters so a regression to
a positional call fails the suite.

This audit reviews the merged state at `origin/main` (commit `6d28cbc`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-segregation issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a location and a concrete proposed fix. The change itself is in excellent
shape; the findings below are residual seams the consolidation surfaced or stale
documentation the merge left behind, not faults in the merged behaviour. None is
tracked by an existing roadmap task (verified against the open phase-7.2/7.3
single-source steps).

## 1. The two parallel builder seams were typed asymmetrically: `line_hit` was widened to `Callable[..., LineHit]`

- **Category:** inconsistency
- **Severity:** medium
- **Location:** `novel_ralph_skill/loaderkit/scan.py:70,88`
  (`line_hit: cabc.Callable[..., LineHit]`) versus
  `novel_ralph_skill/loaderkit/parse.py:73-84` (the new `EntryBuilder[T]`
  `Protocol` with `def __call__(self, entry: Mapping, *, index: int) -> T`).

Task 7.2.7 moved both parameterized seams to a keyword-call convention, but typed
them in opposite ways. The `build_entries` seam gained a precise structural
contract: a new `EntryBuilder[T]` `Protocol` whose `__call__` declares the
keyword-only `(entry, *, index: int)` signature, so a type checker rejects a
builder with the wrong parameter name or kind. The `scan_pattern` seam went the
other way — its `line_hit` annotation was *widened* from the previous
`Callable[[int, int], LineHit]` to `Callable[..., LineHit]`, which accepts a
callable of *any* signature and erases the keyword-only `(*, chapter, line)`
contract from static checking entirely. This is the only `Callable[..., …]` in the
whole `novel_ralph_skill` package, so it stands out as a local anti-pattern, and
it is the weaker of the two parallel seams precisely where the design treats them
as siblings ("the seam that keeps the shared body free of any `Rule`/`Device`
knowledge", repeated verbatim in both modules). A future caller could pass a
`line_hit` with a mismatched keyword signature and the only backstop would be the
runtime `recording_line_hit` test, not the type checker.

- **Proposed fix:** Give `scan_pattern` the same treatment as `build_entries`:
  introduce a `LineHitBuilder` `Protocol` (or a `Callable`-with-named-params alias)
  declaring `def __call__(self, *, chapter: int, line: int) -> LineHit`, and annotate
  `line_hit` with it. This restores the static keyword-signature check the widening
  dropped, removes the lone `Callable[..., …]` from the package, and makes the two
  parallel seams symmetric in both call convention *and* type precision. Pin the
  symmetry with a short comment cross-referencing `EntryBuilder[T]`.

## 2. `BoundCoercion` reintroduces a five-method forwarder surface — the same boilerplate shape the task set out to remove

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/loaderkit/coerce.py:283-303` (the `where`,
  `reject_unknown_keys`, `require`, `require_str`, `require_int` methods of
  `BoundCoercion`, each a one-line delegate to the matching module-level free
  function with `errors=self.errors` supplied).

The task collapsed two *per-family* forwarder modules into one shared bundle —
a real reduction, since the forwarders now live once rather than once per family.
But the bundle itself is a hand-written set of five trivial forwarders, each
re-spelling the underlying free function's signature only to call it back with
`errors=self.errors`. The free functions and the bound methods must now be kept
in lockstep by hand: adding a sixth coercion primitive means editing it in two
places (the free function and a new `BoundCoercion` method), and a signature drift
between the two surfaces would not be caught by the type checker because the method
re-declares rather than inherits the free function's parameters. This is the same
forwarder shape audit-7.2.6 Finding 3 flagged, displaced from the family layer to
the bundle layer rather than eliminated; it is materially better (one copy, not
N) but is not free of the cost.

- **Proposed fix:** This is an acceptable trade-off and may be left as-is, but two
  options reduce the lockstep cost if a third primitive is ever added: (a) bind
  the `errors` argument with `functools.partial` inside `bind_coercion` and store
  the partials as bundle attributes, so there is no re-declared method signature
  to drift; or (b) keep the explicit methods (they are the most readable and
  IDE-navigable form) but add a single unit test that asserts the `BoundCoercion`
  method set is exactly the bind-worthy free-function set, so a future free function
  added without its bound forwarder is caught. If left as-is, a one-line class
  docstring note that the method set must track the module-level helpers would make
  the maintenance contract explicit.

## 3. The developers' guide still describes `_coerce.py` as re-exporting `_require*`/`_where` wrappers and the detector's `line_hit` *lambda*

- **Category:** docs-gap
- **Severity:** medium
- **Location:** `docs/developers-guide.md:1841-1846` (the `_coerce.py`
  "now-thin … re-exports the underscore-named wrappers its `parse.py`/`_fields.py`
  import" passage) and `docs/developers-guide.md:1857,1867-1869` (the
  `scan_pattern` "constructs each hit through a caller-supplied `line_hit`
  callable" / "the detector constructs it in its `line_hit` lambda" passages).

The merge updated the code and the module docstrings but not the developers'
guide, so its loaderkit section now describes the pre-7.2.7 mechanism. Three
specific claims are stale: (i) `_coerce.py` no longer "re-exports the
underscore-named wrappers" — after 7.2.7 it exposes a single `_COERCION`
`BoundCoercion` bundle and call sites read `_COERCION.require_str(...)`, with only
`_ERRORS` and `_Mapping` re-exported; (ii) the "A third pack family … inherits the
primitives by adding one more bundle" sentence is correct but no longer mentions
the `bind_coercion` factory that is now the single binding point a third family
calls; (iii) the `LineHit`-survives-as-runtime-attribute rationale at lines
1867-1869 attributes the surviving import to "its `line_hit` lambda", but 7.2.7
retired that lambda — `LineHit` now stays a runtime import because the detector
passes `line_hit=LineHit` (the class itself). The `by design` conclusion still
holds, but the stated mechanism is wrong, which is worse than silence for a reader
trying to reconcile the prose against the code.

- **Proposed fix:** Refresh the `docs/developers-guide.md` loaderkit section to
  describe the post-7.2.7 state: `_coerce.py` is a single `bind_coercion` call
  yielding a `BoundCoercion` bundle whose methods the family's `parse.py`/
  `_fields.py` call (`_COERCION.require_str(...)`), with `_ERRORS = _COERCION.errors`
  the raw bundle the schema-version/entry-array/pattern-compile primitives still
  bind to directly; and update the `LineHit` runtime-attribute rationale to say
  the detector binds `line_hit=LineHit` directly (the `kw_only` class satisfying
  the
  keyword-call convention), so `LineHit` stays a runtime import without any lambda.
  Mention `bind_coercion` and `BoundCoercion` by name so the guide names the new
  API surface a third family binds.

## 4. The `BoundCoercion.require` / `_fields.py` `allowed_chapters` path remains an `object`-typed value the caller must re-narrow by hand

- **Category:** ergonomics
- **Severity:** low
- **Location:** `novel_ralph_skill/loaderkit/coerce.py:299-303`
  (`BoundCoercion.require` returns `object`) and its sole bound caller
  `novel_ralph_skill/ledger/_fields.py:90-110` (`_allowed_chapters`, which calls
  `_COERCION.require(...)` then re-runs the full `isinstance(... Sequence)` /
  per-element `isinstance(... int)` narrowing by hand).

The bound `require` faithfully forwards the free function's `object` return, so
the one call site that uses it (`_allowed_chapters`) receives an opaque value and
must
re-establish its array-of-positive-int shape with a hand-rolled `isinstance`
ladder. This is the only non-scalar coercion in either family — every other field
goes through `require_str`/`require_int`, which narrow at the boundary — so the
array case is the lone place the bundle leaves the caller holding an unnarrowed
value. It works and is correctly tested by
`test_coerce_binding_wiring.py::test_ledger_bad_allowed_chapters_element_names_device`,
but the asymmetry (scalars narrowed, the one array not) is an ergonomic rough edge
that a third family declaring its own list-typed field would re-encounter.

- **Proposed fix:** Consider adding a `require_int_array` (or a generic
  `require_sequence_of`) primitive to `loaderkit/coerce.py` that performs the
  reject-`str`/`bytes`, reject-empty, reject-non-`int`, reject-non-positive ladder
  once and returns `tuple[int, ...]`, then expose it on `BoundCoercion` and call
  it from `_allowed_chapters`. This narrows the one remaining unnarrowed boundary,
  removes ~20 lines of hand-rolled validation from `_fields.py`, and gives a future
  family a ready-made list primitive. If deferred, this is a candidate for the
  loaderkit-consolidation lineage rather than an in-task fix.

## 5. `make markdownlint`/`make nixie` are still not folded into the `make all` gate

- **Category:** docs-gap
- **Severity:** low
- **Location:** `Makefile` (the `all:` prerequisites versus the standalone
  `markdownlint:` and `nixie:` targets at lines 118-121).

The recurring standing gap, re-noted because this audit's own Markdown artefact
again relied on running both linters by hand rather than an enforced gate. Same
item as `docs/issues/audit-6.3.3.md` Finding 5, `audit-7.2.5.md` Finding 5, and
`audit-7.2.6.md` Finding 5.

- **Proposed fix:** Defer to the existing roadmap handling of this recurring item
  if one exists; otherwise fold `markdownlint nixie` into `make all` (or add a
  docs-lint CI job) so a docs-only change cannot merge without both Markdown gates
  running.
