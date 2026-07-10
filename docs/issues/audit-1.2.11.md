# Post-merge audit — roadmap task 1.2.11

Audit of the codebase after roadmap task 1.2.11 ("Migrate `test_contract_test_deps`
onto the shared conftest fixtures") merged to `main` at commit `4757526`. The
slice itself is correct and discharges the duplication it targeted: the weaker
`split()`-chain distribution-name normalizer and the per-module `pyproject`
re-parse in
[`tests/test_contract_test_deps.py`](../../tests/test_contract_test_deps.py) are
gone, a single `dist_name` fixture now lives in
[`tests/conftest.py`](../../tests/conftest.py), and the
[`tests/test_interrogate_gate.py`](../../tests/test_interrogate_gate.py) consumer
was migrated onto it too. The new fixture carries a parametrized table test
([`tests/test_conftest_helpers.py`](../../tests/test_conftest_helpers.py)) and a
Hypothesis property test, and the developers' guide records the fixture. That
work needs nothing further.

This audit re-checks the wider codebase against the recurring themes carried by
`docs/issues/audit-1.2.1.md` through `docs/issues/audit-1.2.10.md`, and against
the residue the 1.2.11 consolidation left behind. Each finding records a
category, a location, a description, a concrete proposed fix, and a severity.
None is a blocking defect; they are tidy-up opportunities. Findings already
covered by queued roadmap items are noted as such so the root agent does not
double-book them.

Trail followed: explored with `leta` (`leta show`, `leta refs`, `leta files`)
and traced history with `sem`/`git show --commit`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §3.1–3.2, ADR 003
(`docs/adr-003-shared-interface-contract.md`), ADR 004, ADR 005, ADR 006,
`docs/developers-guide.md`, `docs/roadmap.md`, and `AGENTS.md`. Language router:
`python-router` (Python test scaffolding and fixtures).

## Finding 1 — The dev-group declaration check is duplicated across two modules

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`tests/test_contract_test_deps.py:75-80`](../../tests/test_contract_test_deps.py)
  (`test_new_test_deps_are_declared_in_dev_group`),
  [`tests/test_interrogate_gate.py:63-70`](../../tests/test_interrogate_gate.py)
  (`test_interrogate_is_a_dev_dependency`)

The 1.2.11 migration centralized the `dist_name` *normalizer* but left the
surrounding "is this distribution declared in the dev group" idiom copied
verbatim in both consumers. Each module now runs the identical three-line dance:

```python
dev = toml_table(pyproject, "dependency-groups")["dev"]
assert isinstance(dev, list), "[dependency-groups] dev must be a list"
assert any(isinstance(spec, str) and dist_name(spec) == name for spec in dev), ...
```

`test_contract_test_deps.py` loops the check over `("hypothesis", "syrupy")`;
`test_interrogate_gate.py` runs it for the single name `"interrogate"`. The
predicate, the `isinstance(dev, list)` guard, and the `isinstance(spec, str) and
dist_name(spec) == name` membership test are otherwise identical. This is the
same single-source-of-truth principle 1.2.11 itself applied to `dist_name`,
stopped one layer short: a future change to how the dev group is located (for
example a move to `[project.optional-dependencies]` or a normalization rule that
should also lower-case names per PEP 503) must be re-discovered and re-applied in
two places, and a copy that drifts would weaken its module's guarantee silently.

**Proposed fix:** lift a `dev_dependency_names` fixture (or an
`assert_declared_in_dev_group(name)` callable) into `tests/conftest.py` that
reads the dev group through the shared `pyproject`/`toml_table` fixtures and
returns the set of bare distribution names (via `dist_name`), then have both
modules assert membership against it. This collapses the duplicated lookup onto
one home, exactly mirroring the `dist_name` consolidation. `make test` over the
two migrated modules suffices.

## Finding 2 — `dist_name`'s property test lives in the wrong module

- **Category:** separation-of-concerns
- **Severity:** low
- **Location:**
  [`tests/test_interrogate_gate.py:72-113`](../../tests/test_interrogate_gate.py)
  (`test_dist_name_extracts_bare_name_property`),
  [`tests/test_conftest_helpers.py:74-93,141-147`](../../tests/test_conftest_helpers.py)
  (`test_dist_name_extracts_bare_name`, `test_dist_name_returns_none_for_non_name`)

`dist_name` is a shared `conftest` fixture, and
`tests/test_conftest_helpers.py` is described in its own module docstring as the
home for "focused unit tests for the shared `tests/conftest.py` fixtures". The
parametrized table test and the `None`-for-non-name test for `dist_name` correctly
live there. The Hypothesis *property* test for the same fixture, however, was
placed in `test_interrogate_gate.py` — a module whose stated remit is pinning the
"docstring-coverage gate's configuration, invocation, and dependencies". The
property test has nothing to do with the interrogate gate; it landed there only
because that module previously owned the normalizer before 1.2.11 moved it to
`conftest`. A reader looking for the `dist_name` contract finds two thirds of it
in `test_conftest_helpers.py` and the load-bearing third in an unrelated gate
module.

**Proposed fix:** move `test_dist_name_extracts_bare_name_property` (and its
`operator`/`hypothesis.strategies` imports) from `test_interrogate_gate.py` into
`tests/test_conftest_helpers.py` alongside the other `dist_name` tests, leaving
`test_interrogate_gate.py` to test only the gate. The closure-fixture convention
the property test follows (resolving the function-scoped fixture in the outer
test and passing it into the inner `@given` body) is unchanged by the move.
`make test` confirms the relocation.

## Finding 3 — The render_human empty-messages branch is still unexercised (carried)

- **Category:** test-gap
- **Severity:** medium
- **Location:**
  [`novel_ralph_skill/contract/envelope.py:169-170`](../../novel_ralph_skill/contract/envelope.py)
  (the `else` arm emitting `messages: (none)`),
  [`tests/test_contract_envelope.py`](../../tests/test_contract_envelope.py)

First raised as `audit-1.2.10.md` Finding 1 and untouched by 1.2.11. Every
`render_human` test in the suite still passes a non-empty `messages` sequence
(`test_render_human_lists_messages_without_result_json` passes two notes, and
`test_render_human_success_snapshot` passes one), so the `if env.messages:` branch
is always taken and the `else` branch emitting the literal `messages: (none)` line
for a message-less envelope is dead with respect to the suite. A success envelope
with no human prose is a real, expected shape (a checker that is satisfied and has
nothing to say), so the unrendered branch is exactly the path a future edit could
break unnoticed.

**Proposed fix:** add a focused test that builds an envelope with `messages=[]`
and asserts `render_human(env)` contains the literal `messages: (none)` line and
does *not* contain a two-space-and-dash message bullet; a syrupy snapshot of the
empty-messages rendering would also pin the exact line. `make test` over the new
case suffices.

## Finding 4 — A third copy of the wrapper-configured app builder (carried; roadmap 1.2.21)

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`tests/test_contract_runner.py`](../../tests/test_contract_runner.py)
  (`_build_app`),
  [`tests/test_contract_properties.py`](../../tests/test_contract_properties.py)
  (`_build_app`),
  [`tests/test_cyclopts_contract.py:49`](../../tests/test_cyclopts_contract.py)
  (`_make_app`)

Carried from `audit-1.2.8.md` Finding 3 and `audit-1.2.10.md` Finding 2, and
untouched by 1.2.11. Three test modules each build a Cyclopts app with the same
load-bearing `result_action="return_value", exit_on_error=False,
print_error=False, help_on_error=False` configuration the `run` wrapper requires.
A future cyclopts upgrade that changes one of those keyword defaults must be
re-discovered and re-fixed three times.

**Proposed fix:** roadmap task 1.2.21 already covers extracting a shared
wrapper-app builder fixture into `tests/conftest.py`. No new roadmap item is
needed; flagged here only to record that 1.2.11 did not touch it.

## Finding 5 — `STUB_EXIT_CODE` re-spells the contract's usage-error code as a bare literal (carried)

- **Category:** inconsistency
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/commands/stub.py:18`](../../novel_ralph_skill/commands/stub.py)
  (`STUB_EXIT_CODE = 2`),
  [`novel_ralph_skill/contract/exit_codes.py:26`](../../novel_ralph_skill/contract/exit_codes.py)
  (`ExitCode.USAGE_ERROR = 2`)

Carried from `audit-1.2.10.md` Finding 6. The stub module defines
`STUB_EXIT_CODE = 2` with a docstring naming it "usage error, design 3.2", which
is exactly `ExitCode.USAGE_ERROR`. The contract package now exists as the single
source of truth for the exit-code vocabulary, yet the stub hard-codes the integer
`2` independently. If a future contract revision renumbered the usage-error code,
the stubs would silently diverge from the contract they honour.

**Proposed fix:** import `ExitCode` from `novel_ralph_skill.contract.exit_codes`
and define `STUB_EXIT_CODE = ExitCode.USAGE_ERROR` (or use the enum member
directly in the `sys.exit` call). Because `ExitCode` subclasses `int`, behaviour
is unchanged. Best sequenced when the stubs adopt the envelope contract (roadmap
1.3.x) so they migrate onto the contract module in one move. Not yet a roadmap
item.

## Finding 6 — Four near-identical locked-version-pin guards lack a shared shape (carried/widened)

- **Category:** similarity
- **Severity:** low
- **Location:**
  [`tests/test_tomlkit_dependency.py:24,31-39`](../../tests/test_tomlkit_dependency.py)
  (`LOCKED_TOMLKIT_VERSION`),
  [`tests/test_cyclopts_contract.py:46,74-82`](../../tests/test_cyclopts_contract.py)
  (`LOCKED_CYCLOPTS_VERSION`),
  [`tests/test_contract_test_deps.py:29-30,33-55`](../../tests/test_contract_test_deps.py)
  (`LOCKED_HYPOTHESIS_VERSION`, `LOCKED_SYRUPY_VERSION`)

Four locked-version tripwires now follow the same pattern: a `LOCKED_X_VERSION`
constant and an assertion that the resolved version (via `module.__version__` or
`importlib.metadata.version`) equals the pin. The bodies and commentary differ
just enough that this is a *similarity*, not a clean duplication — each carries
bespoke rationale (tomlkit's round-trip risk, cyclopts's exit-code-contract risk,
the dev-deps tripwire). They are not wrong, but as the spine grows more pinned
dependencies the pattern will multiply, and there is no shared helper to keep the
"read the resolved version, compare to the pin" mechanics consistent (note that
`syrupy` already needs the `importlib.metadata.version` fallback because it
exposes no `__version__`, a wrinkle each future pin must rediscover).

**Proposed fix:** consider a small shared `assert_locked_version(distribution,
expected)` helper (or `resolved_version` fixture) in `tests/conftest.py` that
prefers `importlib.metadata.version` uniformly, so each guard reduces to one
call plus its bespoke rationale comment. This is lower priority than Findings 1–3
and is genuinely optional — the per-module commentary is the load-bearing part —
so weigh it against the value of leaving each tripwire self-contained. Not a
roadmap item; offered as a watch-this-pattern note.

## Finding 7 — Leftover project-template scaffold is unrelated to the harness (carried)

- **Category:** separation-of-concerns
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/pure.py`](../../novel_ralph_skill/pure.py),
  [`novel_ralph_skill/__init__.py`](../../novel_ralph_skill/__init__.py),
  [`tests/test_stub.py`](../../tests/test_stub.py)

Carried from `audit-1.2.10.md` Finding 5. `pure.py` exports a single `hello()`
returning `"hello from Python"`, `__init__.py` carries the matching
Rust-or-Python fallback wiring, and `test_stub.py` asserts the greeting. This is
boilerplate from the pure-Python project template, not part of the deterministic
spine: there is no Rust extension in this repository and `hello` is not part of
the contract surface (ADR 003). A reader opening `__init__.py` first meets
template greeting machinery rather than the command/contract architecture.

**Proposed fix:** decide the package's intended public entry shape and either
(a) remove `pure.py`, the `hello` re-export, and `test_stub.py`, trimming
`__init__.py` to the genuine package surface; or (b) if a `_rs` accelerator is
genuinely planned, record that intent in a short ADR so the fallback wiring reads
as deliberate. The design names no Rust component, so (a) is the likelier correct
call. Not yet a roadmap item; offered for the root agent to track.

## Notes on what was checked and found sound

- The 1.2.11 `dist_name` fixture is well-formed: the regex is anchored, the
  normalization is the single home for the concept, and the property test
  correctly resolves the function-scoped fixture outside the `@given` body so
  `HealthCheck.function_scoped_fixture` cannot fire (Finding 2 concerns only its
  *location*, not its correctness).
- The `run` wrapper (`contract/runner.py`) cleanly separates command bodies from
  exit-code translation and envelope emission. No command-query-separation
  violation found: `build_envelope` and `is_ok` are pure queries, `_emit`/`run`
  are the commands, and the boundary is clean.
- `build_envelope` deriving `ok` from `is_ok(code)` (rather than accepting it as
  a parameter) correctly forecloses the inconsistent-`ok` failure mode, and
  `render_machine` building the ordered dict explicitly is a deliberate choice
  that pins the contract field order.
- The command-names registry (`commands/names.py`) remains the single source of
  truth, with `MappingProxyType` guarding the underlying dict and
  `project_scripts_table` returning a fresh dict per call.
- `interrogate` 100% docstring coverage is enforced and pinned by a static gate;
  the migrated `test_contract_test_deps.py` and `test_interrogate_gate.py` both
  carry full numpydoc docstrings and pass through the shared fixtures without a
  cross-module import.
