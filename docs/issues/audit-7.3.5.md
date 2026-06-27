# Post-merge audit — roadmap task 7.3.5

Audit of the codebase after roadmap task 7.3.5 ("Collapse the
`novel.main`/`stub._drive` entry-point duplication into one shared drive seam")
merged to `main` at commit `ed0c0bd`. The slice lifts the
build-`RunContext`-then-call-`run` plumbing out of the `novel` multiplexer
entry point and into a new contract-level
[`drive`](../../novel_ralph_skill/contract/runner.py) seam, re-exports it from
the contract package, and repoints
[`novel.main`](../../novel_ralph_skill/commands/novel.py) onto it. The
`stub._drive` copy the reroute named had already been retired by 1.2.15 (ADR
007), so no live duplicate survived to collapse; the slice delivered the
constructive arm — one explicit home for the plumbing — instead. It adds a
seam-forwards-to-`run` unit test
([`tests/test_contract_drive_seam.py`](../../tests/test_contract_drive_seam.py)),
a structural single-home guard
([`tests/test_entry_point_single_home.py`](../../tests/test_entry_point_single_home.py)),
and a contract-to-commands layering guard
([`tests/test_contract_layering.py`](../../tests/test_contract_layering.py)),
and refreshes the developers' guide.

The slice is sound and discharges its success criterion: the
parse-`--human`/resolve-name/drive-via-`run` plumbing lives in one
contract-level seam parametrised by already-resolved scalars, `novel.main`
delegates rather than re-spelling it, the contract -> commands layering is held
statically, and the import-laziness profile is preserved. The docstrings on the
new seam are exemplary, and the layering and single-home guards are unusually
careful (they read source statically rather than importing the runner at
collection time). The findings below are tidy-ups across duplication,
ergonomics, and coverage; none is a blocking defect, and none weakens the new
seam or its guards.

This audit reviews the merged state at `origin/main` (commit `ed0c0bd`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-separation (CQS) issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a category, a location, a description, a concrete proposed fix, and a
severity. The trail: design §4 and §3.2, ADR 003 (shared interface contract),
ADR 007 (novel multiplexer surface), `docs/developers-guide.md`,
`docs/scripting-standards.md`, and the execplan
[`docs/execplans/roadmap-7-3-5.md`](../execplans/roadmap-7-3-5.md). Navigation
used `leta` and history used `sem`.

## Finding 1 — Duplicated AST-scanner helpers across the two new guard tests

- Category: duplication
- Severity: medium
- Location:
  [`tests/test_contract_layering.py`](../../tests/test_contract_layering.py)
  (`_callee_name`, the `_NESTED_SCOPES` prune, the module-walk loop) and
  [`tests/test_entry_point_single_home.py`](../../tests/test_entry_point_single_home.py)
  (`_callee_name`, the `nested_scopes` prune in `_calls_in_executable_body`).

The two guard modules the slice adds each carry their own copy of the same
AST-walk primitives. `_callee_name` — return an `ast.Call`'s simple callee name
(`Name.id` or `Attribute.attr`, else `None`) — is byte-for-byte identical in
both files, docstring included. Both also re-implement the
"walk-the-tree-but-prune-at-nested-scope-boundaries" loop: `test_contract_layering`
prunes at `FunctionDef`/`AsyncFunctionDef`/`Lambda` to find module-scope
imports, and `test_entry_point_single_home` prunes at the same set plus
`ClassDef` to find a function body's direct calls. The pruning rationale (a
nested scope's body does not run in the parent's frame) is spelled out twice in
near-identical prose. The repo already establishes the shared-scanner-helper
pattern for non-AST guards
([`tests/_skill_contract_scanner.py`](../../tests/_skill_contract_scanner.py),
[`tests/_state_layout_scanner.py`](../../tests/_state_layout_scanner.py)), so
this is a divergence from an existing convention, not a new abstraction.

Proposed fix: extract the shared primitives into a `tests/_ast_scan.py` support
module — `callee_name(call)`, a `nested_scope` predicate (or the
`_NESTED_SCOPES` tuple), and a `module_scope_calls`/`scope_local_calls`
walker that takes the prune set — and have both guard modules import them.
Keep the import-resolution logic (`_resolve_import_from`,
`_resolve_dynamic_import`) in the same module since it is the layering guard's
substantive payload. This removes the duplicate `_callee_name` and the
twice-told prune loop, and gives the next AST guard (there will be one —
`test_state_sourcing_home` and the mount-table laziness guard already parse
source) a single home to build on.

## Finding 2 — `drive` decomposes then immediately rebuilds a `RunContext`, forcing a lint suppression

- Category: ergonomics
- Severity: low
- Location:
  [`novel_ralph_skill/contract/runner.py`](../../novel_ralph_skill/contract/runner.py)
  (`drive`, the `# noqa: PLR0913  # pylint: disable=too-many-arguments` on the
  signature).

`drive(app, argv, *, command, working_dir, human)` takes the three scalars
`RunContext` already bundles, then its one-line body reconstructs a
`RunContext(command=command, working_dir=working_dir, human=human)` and forwards
to `run`. The decomposition pushes the signature to five parameters, which trips
`PLR0913` and needs a dual `noqa`/`pylint: disable` suppression — the only such
double-barrelled argument-count suppression the slice introduces. The execplan
justifies keeping name/dir resolution in the caller for the contract -> commands
layering, which is correct, but that argument is about *resolution*, not about
*how the resolved trio is passed*: a caller that already holds the three values
could equally pass a `RunContext`.

Proposed fix: consider `drive(app, argv, context)` taking the already-built
`RunContext` (the sole production caller, `novel.main`, constructs it inline at
the call site; the seam still imports no commands module, so layering is
untouched). This drops the parameter count below the `PLR0913` threshold and
removes both suppressions. If the keyword-scalar form is deliberately preferred
(so `main` never names `RunContext`, keeping the single-home guard's
forbidden-callee list meaningful), record that trade-off in the `drive`
docstring's `Notes` so the suppression reads as a decision rather than an
oversight — at present the docstring explains *why resolution stays in the
caller*, not *why the context is passed disassembled*.

## Finding 3 — `_command_name_for`'s unknown-verb and bare-`novel` fallbacks are unit-tested only indirectly

- Category: test-gap
- Severity: low
- Location:
  [`novel_ralph_skill/commands/novel.py`](../../novel_ralph_skill/commands/novel.py)
  (`_command_name_for`).

`_command_name_for` carries the slice's most load-bearing conditional: it maps
the leading non-flag token to its spaced registry name, and falls back to the
bare `"novel"` for three distinct cases — no non-flag token (bare `novel` or a
leading global flag), an unregistered token, and (per the docstring) a stray
value left by a hypothetical value-carrying global flag. The docstring reasons
carefully about all three, but the function has no direct unit test pinning the
branch table; its behaviour is exercised only transitively through the
multiplexer behaviour/dispatch suites and the migrated 1.3.6 routing tripwire,
which assert end-to-end envelope command names rather than the resolver's
branches in isolation.

Proposed fix: add a small parametrised unit test (alongside the existing
multiplexer support in `tests/`) that drives `_command_name_for` directly over:
a registered verb (`["state", "check"]` -> `"novel state"`); a bare invocation
(`[]` -> `"novel"`); a leading flag (`["--help"]` -> `"novel"`); an unknown verb
(`["bogus"]` -> `"novel"`); and a stray-value-after-flag shape
(`["foo.toml", "state"]` -> `"novel"`, pinning the documented "stray value can
never be stamped as a subcommand" guarantee). This converts the docstring's
three-case reasoning into an executable contract so a future global flag that
breaks the value-less assumption fails loudly here.

## Finding 4 — `make_contract_app`'s `name` parameter has no direct contract test

- Category: test-gap
- Severity: low
- Location:
  [`novel_ralph_skill/contract/runner.py`](../../novel_ralph_skill/contract/runner.py)
  (`make_contract_app`).

The slice's `drive` and the multiplexer both lean on `make_contract_app(name)`
to stamp the four-flag contract. The factory's docstring promises the returned
app carries the four flags *and* `name`, but the existing app-factory coverage
([`tests/test_contract_app_factory.py`](../../tests/test_contract_app_factory.py))
pins the four flags; the `name` round-trip (the value passed in is the value the
app exposes) is not asserted directly. Since `build_multiplexer` now relies on
`make_contract_app(MULTIPLEXER_NAME)` to set the parent app's name correctly
(and the envelope `command` stamping rides on it), a silent regression in the
name argument would surface only obliquely.

Proposed fix: extend `test_contract_app_factory.py` with one assertion that
`make_contract_app("novel-state").name == "novel-state"` (per Cyclopts's name
exposure), closing the gap between the factory docstring's promise and its
verified surface. This is a single-line addition to an existing test.

## Finding 5 — Developers' guide describes the `drive` seam but the contract package's public-surface list is the only place `drive` is catalogued

- Category: docs-gap
- Severity: low
- Location:
  [`novel_ralph_skill/contract/__init__.py`](../../novel_ralph_skill/contract/__init__.py)
  (module docstring's re-export inventory) and
  [`docs/developers-guide.md`](../../docs/developers-guide.md) (the entry-point
  subsection).

The contract package docstring enumerates the public surface as a flat prose
list and now ends with "…, :func:`run`, and :func:`drive`." The developers'
guide explains the `main -> drive -> run` routing well, but neither document
states the *layering distinction* between `run` and `drive` that the slice
establishes: `run` is the exit-code/envelope wrapper, whereas `drive` is the
thin context-assembly seam that owns nothing `run` owns. A reader scanning the
re-export list sees two adjacent verbs (`run`, `drive`) with no cue as to which
to reach for. This is a minor orientation gap, not a contradiction.

Proposed fix: add one clause to the contract package docstring distinguishing
the two — e.g. ":func:`run` (the exit-code/envelope wrapper) and :func:`drive`
(the entry-point context-assembly seam that forwards to :func:`run`)" — so the
re-export inventory carries the same `run`-vs-`drive` distinction the
developers' guide now implies. No code change.

## Finding 6 — The two single-home guards and the migrated 1.3.6 tripwire describe one surface across three files with cross-references but no single index

- Category: separation-of-concerns
- Severity: low
- Location:
  [`tests/test_entry_point_single_home.py`](../../tests/test_entry_point_single_home.py),
  [`tests/test_contract_drive_seam.py`](../../tests/test_contract_drive_seam.py),
  and the migrated tripwire in
  `tests/test_contract_app_centralisation.py::test_novel_entry_point_routes_through_the_shared_seam`.

The `main -> drive -> run` invariant is now pinned by three tests in three
modules: the entry-point *half* (`main` routes through `drive`, no inline
`run`/`RunContext`) in `test_entry_point_single_home`, the seam *half* (`drive`
forwards to `run` under a faithful context) in `test_contract_drive_seam`, and
the end-to-end routing tripwire in `test_contract_app_centralisation`. Each
module's docstring cross-references the others, which is good discipline, but
the split means a maintainer must read three headers to reconstruct the whole
invariant, and a future reader cannot tell from any one file that it is one
third of a contract. The cross-references are accurate today but are prose, so
they drift silently if a module is renamed.

Proposed fix: this is a deliberate and defensible split (seam unit vs entry-point
structure vs end-to-end behaviour), so the recommendation is documentation, not
consolidation: add a one-line "transitive invariant" note to the developers'
guide entry-point subsection naming all three guards and the half each owns, so
the single authoritative index lives in the guide rather than being reconstructed
from three test docstrings. Optionally co-locate the two new guard modules'
shared framing by giving them a common docstring stem.

## Summary

Task 7.3.5 is a clean, well-guarded refactor: the entry-point drive plumbing now
has one contract-level home, the contract -> commands layering and the
import-laziness profile are held by static guards, and the new seam is
generously documented. No finding blocks. The highest-value follow-up is Finding
1 (extract the duplicated AST-scanner helpers into a shared `tests/_ast_scan.py`
support module, matching the repo's existing scanner-helper convention), since
the duplication will only grow as more structural guards are added. Findings 2–6
are ergonomic and coverage tidy-ups that harden the seam's contract and close
small gaps between docstring promises and verified behaviour.
