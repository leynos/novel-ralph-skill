# Post-merge audit — roadmap task 1.3.6

Audit of the codebase after task 1.3.6 ("Add a shared contract-app factory for
the runner's required four-flag `cyclopts.App`") merged to `main` at commit
`af7ef1d`. The task introduced
`novel_ralph_skill.contract.runner.make_contract_app(name)`, which co-locates the
runner's hard requirement (`result_action="return_value"`, `exit_on_error=False`,
`print_error=False`, `help_on_error=False`) in one place, beside the `run`
wrapper that demands it. The four real `build_app()` constructors
(`novel_state`, `_compile`, `_desloppify`, `_novel_done`) and the `wrapper_app`
test fixture now route through the factory rather than re-spelling the flags, and
the four `stub.py` entry-point bodies collapse onto a shared `_drive(name,
build_app)` helper so the `parse_global_flags`/`run` plumbing is defined once.
The slice ships a `tests/test_contract_app_factory.py` unit suite and re-exports
the factory from the `contract` package.

The implementation is of a high standard and meets its success criterion: the
four-flag contract has a single home, the constructors and entry-point bodies
consume it, and the suites stay green. The findings below are refinement
opportunities, not defects; none blocks the merge. Several are continuations of
the same single-home discipline the task itself advanced.

Trail followed: `docs/novel-ralph-harness-design.md` §§3.1/3.2/4,
`docs/adr-003-shared-interface-contract.md`, `docs/developers-guide.md`,
`docs/issues/audit-3.1.1.md` (Finding 5, the reroute this task discharged), and
the source under `novel_ralph_skill/contract/` and `novel_ralph_skill/commands/`.
Navigation used `leta` (`files`, `show`, `refs`); history used `sem`/`git show`.
Skills consulted: `leta`, `python-router` (routing to `python-types-and-apis`
and `python-testing`).

## Finding 1 — Stale hardcoded line reference in `make_contract_app` docstring (docs-gap)

**Location**: `novel_ralph_skill/contract/runner.py:58`.

The new factory docstring says the four-flag contract is "specified in the `run`
docstring (runner.py lines 166-170)". In the merged file the four-flag spec sits
in the `run` docstring at lines 197-201; lines 166-170 are inside `RunContext`
and `_emit`. The reference was already stale on landing — a line-number citation
to a symbol in the same file is a maintenance trap that drifts on the next edit.

**Proposed fix**: Replace the line-number citation with a symbol reference, e.g.
"specified in the :func:`run` docstring" (drop the parenthetical line range), or
cite the design/ADR location once it documents the flags (see Finding 6). The
same pattern recurs at `novel_ralph_skill/rulepack/packs/ai-isms.toml:20`
(`detect.py:147-200`, now `_scan_rule`/`_finding` at 148-237); fix both and
prefer symbol names over line numbers in prose throughout.

**Severity**: low.

## Finding 2 — `_load_or_state_error` is a cross-module dependency wearing a private name (separation-of-concerns)

**Location**: `novel_ralph_skill/commands/novel_state.py:129`
(`_load_or_state_error`), imported by
`novel_ralph_skill/commands/_compile.py:36`,
`novel_ralph_skill/commands/_desloppify.py:45`, and
`novel_ralph_skill/commands/_novel_done.py:32`.

The underscore prefix advertises module-private intent, yet three sibling command
modules import and depend on it. Alongside `STATE_INPUT_ERRORS`,
`WORKING_DIR_NAME`, `state_path`, and `working_dir` — also imported across
`_compile`, `_desloppify`, `_novel_done`, `_recount`, `_state_mutators`, and
`stub` — `novel_state.py` (nominally the `novel-state` *command* module) has
become the de-facto home for the shared state-sourcing surface. A reader cannot
tell from the name which symbols are the command's internals and which are the
contract every command leans on, and a future refactor of `novel-state` risks
silently breaking four other commands.

**Proposed fix**: Lift the shared state-sourcing seam — `WORKING_DIR_NAME`,
`state_path`, `working_dir`, `STATE_INPUT_ERRORS`, and the load-and-translate
helper (renamed `load_or_state_error`, public) — into a small dedicated module
(e.g. `novel_ralph_skill/commands/_state_io.py` or
`novel_ralph_skill/state/sourcing.py`), and have `novel_state` consume it like
its siblings. This makes the shared contract explicit and frees `novel_state.py`
to own only the `novel-state` app. This mirrors the single-home discipline that
tasks 1.3.3, 1.3.4, and 1.3.6 itself applied to the contract package.

**Severity**: medium.

## Finding 3 — No test pins that the real `build_app()` constructors carry the four flags (test-gap)

**Location**: `tests/test_contract_app_factory.py` (pins the factory only);
`novel_ralph_skill/commands/{novel_state,_compile,_desloppify,_novel_done}.py`
`build_app` constructors (unguarded).

The factory test asserts that `make_contract_app` carries the four flags, and
`test_cyclopts_contract.py` pins raw Cyclopts behaviour, but nothing asserts that
each production `build_app()` *result* carries `result_action=("return_value",)`,
`exit_on_error is False`, `print_error is False`, and `help_on_error is False`.
A command could regress to a bare `cyclopts.App(name=...)` and the factory's own
test would stay green. Such a regression would be caught only by an end-to-end
test that exercises a usage error and asserts exit `2` plus a machine envelope —
coverage that is present for `desloppify` and the console-scripts suite but not
visibly for `novel-compile` or `novel-done`'s usage path.

**Proposed fix**: Add a small parametrized regression test over the four
`build_app` callables (and `make_stub_app` if it should join the contract — see
Finding 4) asserting the four flag values on the constructed app. This is the
cheap structural tripwire the factory makes possible; it guards the "constructors
consume the factory" half of the success criterion that the current suite leaves
implicit.

**Severity**: medium.

## Finding 4 — `make_stub_app` builds a bare app inconsistent with the contract factory (inconsistency)

**Location**: `novel_ralph_skill/commands/stub.py:63`
(`cyclopts.App(name=name)`), versus the four-flag `make_contract_app`; and
`stub.py:137` (`wordcount()` calls the stub app directly, bypassing `_drive`/`run`).

The `wordcount` stub deliberately predates the envelope contract (documented at
`stub.py:69` — the JSON envelope is task 1.3.1) and exits `2` via a raw
`STUB_EXIT_CODE = 2` literal that duplicates `ExitCode.USAGE_ERROR`'s value
rather than referencing it. With the factory now the single home for the
four-flag contract, the bare `cyclopts.App(name=name)` and the standalone exit
literal stand out as the one command that neither consumes the factory nor names
its exit code through the shared `ExitCode` vocabulary.

**Proposed fix**: When `wordcount` lands its real slice, route it through
`make_contract_app` and `_drive` like its siblings. In the interim, at minimum
define `STUB_EXIT_CODE = ExitCode.USAGE_ERROR` (an `IntEnum`, so the literal
value and `sys.exit` semantics are unchanged) so the stub names its exit through
the shared vocabulary rather than re-spelling `2`. Record the bare-app/raw-literal
divergence as deliberate-until-the-slice in the `stub.py` module docstring so the
next reader does not mistake it for drift.

**Severity**: low.

## Finding 5 — The cyclopts tripwire still re-spells the four flags inline (duplication)

**Location**: `tests/test_cyclopts_contract.py:59-64` (`_make_app`).

Task 1.3.6 set out to eliminate the four-flag re-spelling across the codebase, and
it cleared every production constructor and the `wrapper_app` fixture. The
`_make_app` helper in the cyclopts tripwire still constructs the flags inline,
leaving one residual copy of the exact tuple the task consolidated. This copy is
arguably defensible — the tripwire's purpose is to pin *raw Cyclopts* behaviour
independent of project code, so threading it through `make_contract_app` would
couple the version tripwire to the factory it is meant to underpin. The audit
records it for visibility rather than as a clear defect.

**Proposed fix**: Either leave it with a one-line comment stating the inline
construction is intentional (the tripwire pins Cyclopts, not the factory), or, if
the team prefers full single-homing, have `_make_app` call `make_contract_app`
and register its `greet` body on the result. Prefer the comment: the tripwire
should fail on a Cyclopts default change even if the factory is broken.

**Severity**: low.

## Finding 6 — The four-flag contract is undocumented in ADR-003 and the design (docs-gap)

**Location**: `docs/adr-003-shared-interface-contract.md`,
`docs/novel-ralph-harness-design.md`, `docs/developers-guide.md`; the gap is
acknowledged in-code at `novel_ralph_skill/contract/runner.py:58-60` ("the flags
serve the exit-code policy in design §3.2 / ADR-003 Table 2 but are not
documented there").

The four-flag `cyclopts.App` requirement is now load-bearing contract machinery
with a dedicated factory, but it appears nowhere in the prose record. ADR-003 is
the shared-interface-contract ADR and the natural home for "every command's app
MUST be built with these four flags, via `make_contract_app`, so the `run`
wrapper owns every exit and envelope." Neither the developers' guide nor the
users' guide mentions the factory.

**Proposed fix**: Add a short subsection to ADR-003 (or a "Technical
requirements" addendum) recording the four-flag requirement, why each flag is
needed, and that `make_contract_app` is its single enforcement point. Add a brief
mention to the developers' guide command-surface section so a contributor adding
a sixth command knows to call the factory rather than `cyclopts.App` directly. Once
documented, retarget the `runner.py` docstring's flag citation (Finding 1) at the
ADR.

**Severity**: low.

## Finding 7 — `wrapper_app` fixture borrows `COMMAND_NAMES[0]` as an arbitrary name (ergonomics)

**Location**: `tests/conftest.py` (`wrapper_app._build`, the
`make_contract_app(COMMAND_NAMES[0])` call introduced by this task).

The factory requires a `name` where the fixture was previously anonymous. The
fixture now reaches into `COMMAND_NAMES[0]` — a positional index into the command
registry — to satisfy the parameter, with an inline comment noting the name is
"behaviourally inert for the run path". Coupling a generic test fixture to
whichever command happens to sort first in the registry is a subtle, surprising
dependency: a registry reorder would silently change the fixture's app name, and
a reader must read the comment to learn the name is inert.

**Proposed fix**: Pass an explicit, self-describing literal such as
`make_contract_app("contract-test-app")` (or a module-level
`_FIXTURE_APP_NAME` constant) so the inertness is obvious from the call site and
the fixture carries no incidental dependency on registry ordering.

**Severity**: low.
