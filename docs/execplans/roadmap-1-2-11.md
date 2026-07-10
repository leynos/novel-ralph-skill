# Migrate `test_contract_test_deps` onto shared conftest fixtures and centralize dependency-name normalization

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: COMPLETE (all four work items implemented, gated, and committed;
round-1 review blocking points B1 and B2 resolved; advisories A1, A2, A3, A4
addressed)

## Purpose / big picture

Roadmap task 1.2.7 consolidated the test suite's shared scaffolding into
[`tests/conftest.py`](../../tests/conftest.py) and migrated six modules onto it.
A seventh module — [`tests/test_contract_test_deps.py`](../../tests/test_contract_test_deps.py),
landed in parallel by roadmap task 1.3.1 — never reached that home. The
post-merge audit [`docs/issues/audit-1.2.7.md`](../issues/audit-1.2.7.md)
Findings 1 and 2 record the two resulting duplications:

1. `test_contract_test_deps` is the seventh test module to resolve and parse
   `pyproject.toml` itself (`_PYPROJECT` plus `_dev_dependencies`), re-creating
   exactly the parse-duplication the `pyproject` and `toml_table` fixtures were
   built to remove.
2. A second, weaker copy of PEP 508 distribution-name normalization lives in
   `test_contract_test_deps` as the inline expression
   `spec.split()[0].split(">")[0].split("=")[0]`. The canonical, documented
   normalizer is `_dist_name` (backed by the `_DIST_NAME` regex) in
   [`tests/test_interrogate_gate.py`](../../tests/test_interrogate_gate.py). The
   two copies disagree: the `split`-chain leaks extras brackets, several version
   operators, and environment markers into the "name", so a legitimate future
   edit such as `hypothesis[cli]>=6.0` would make the assertion spuriously fail.

After this change, the dependency-name normalizer lives once in
`tests/conftest.py` as a `dist_name` fixture, both `test_interrogate_gate` and
`test_contract_test_deps` consume it by fixture name, and
`test_contract_test_deps` reads the dev-dependency group through the shared
`pyproject`/`toml_table` fixtures with no per-module `pyproject` parse. This can
be verified by running `make all`: the suite stays green, the new `dist_name`
fixture tests in `tests/test_conftest_helpers.py` pass, and grepping the
`tests/` tree shows neither `_PYPROJECT` nor the `split`-chain survives.

This is a test-internal refactor only. It touches no console-script behaviour,
no `state.toml` handling, no cuprum execution path, and no production package
module.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Do not modify any file outside the worktree
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-11`. The
  root/control worktree is off-limits for edits.
- Do not change the observable guarantees of any test. The two version-pin
  tests `test_hypothesis_import_and_version` and `test_syrupy_version` read
  installed distribution metadata, not `pyproject.toml`; they must keep their
  exact pins (`LOCKED_HYPOTHESIS_VERSION = "6.155.7"`,
  `LOCKED_SYRUPY_VERSION = "5.3.2"`) and behaviour unchanged (audit-1.2.7
  Finding 1, "the two version-pin tests … stay as they are").
- Do not weaken any guard. The migrated `test_interrogate_gate` assertions must
  keep behaving as before; the `dist_name` fixture must reproduce `_dist_name`'s
  semantics exactly so the interrogate guard's meaning is preserved.
- `tests/conftest.py` is inside `$(PYTHON_TARGETS)` and is NOT matched by the
  Ruff `**/test_*.py` `per-file-ignores` glob (`pyproject.toml:96`). Any helper
  added there must therefore carry a full docstring and must NOT use a bare
  `assert`; failure paths raise `AssertionError` directly. The `dist_name`
  normalizer returns `str | None` and raises nothing, so this is satisfied by
  construction. (Developers' guide §"Shared test scaffolding".)
- Keep the shared-scaffolding convention: consume helpers by fixture name; never
  import from `conftest` or another test module's private symbols (developers'
  guide §"Shared test scaffolding"; AGENTS.md "Python verification and
  testing").
- Prose, comments, and commits use en-GB Oxford spelling ("-ize"/"-yse"/"-our")
  per AGENTS.md and the `en-gb-oxendict` convention. Note: "normalize" stays
  "-ise" (it is not an "-ize" word under Oxford rules — Oxford spelling applies
  "-ize" only where the Greek `-izo` root warrants it; "normalize" follows the
  French-derived stem and stays "-ise" in Oxford usage, matching the existing
  codebase spelling in `test_interrogate_gate.py` and the roadmap entry).

## Tolerances (exception triggers)

- Scope: if implementation requires editing more than 5 files or more than ~120
  net lines, stop and escalate. Expected footprint: `tests/conftest.py`,
  `tests/test_contract_test_deps.py`, `tests/test_interrogate_gate.py`,
  `tests/test_conftest_helpers.py`, and `docs/developers-guide.md` — five files.
- Interface: if the shared `dist_name` fixture would need a signature other than
  a `(spec: str) -> str | None` callable to satisfy both consumers, stop and
  escalate.
- Dependencies: if any work item appears to need a new external dependency, stop
  and escalate. None is expected; `hypothesis` is already a locked dependency
  (`pyproject.toml:28`, `uv.lock`).
- Iterations: if `make all` still fails after 3 fix attempts on any single work
  item, stop and escalate with the failing output captured in `Decision Log`.
- Ambiguity: if a reviewer or the audit text implies a behaviour for the
  normalizer that the `_DIST_NAME` regex does not already provide, stop and
  present options rather than inventing semantics.

## Risks

- Risk: `tomllib` and `pathlib` imports become unused in
  `test_contract_test_deps` after migration, tripping Ruff F401.
  Severity: low. Likelihood: high.
  Mitigation: Work item 2 deletes the now-dead imports in the same edit and
  validates with `make all` (Ruff F401/F811 run inside `make lint`).
- Risk: the `dist_name` fixture's regex semantics drift from the original
  `_dist_name`, silently weakening the interrogate guard.
  Severity: medium. Likelihood: low.
  Mitigation: Work item 1 lifts the exact `_DIST_NAME` pattern verbatim and
  pins its semantics with parametrized unit tests plus a Hypothesis property
  test (work item 3) that asserts the bare-name invariant over generated
  specifiers.
- Risk: a fixture-name collision or fixture-resolution surprise (e.g.
  `dist_name` shadowed by a local name) breaks one consumer.
  Severity: low. Likelihood: low.
  Mitigation: `dist_name` is a new, unique fixture name; both consumers take
  it as a test-method parameter. `make test` exercises both modules.
- Risk: the property test is slow or flaky under `pytest-xdist`, or trips the
  `timeout = 30` `pytest-timeout` ceiling (`pyproject.toml:325`) under `-n auto`.
  Severity: low. Likelihood: low.
  Mitigation: Keep the strategy small and deterministic (bounded text
  alphabets, no external state, default Hypothesis settings). The property is
  pure and fast; xdist distributes whole test functions, so a single property
  test runs on one worker with no shared state. The existing property suite
  `tests/test_contract_properties.py` already coexists with this exact ceiling
  under the same configuration, so this is precedent, not first-principles
  reasoning (advisory A3).
- Risk (B1, determinate, RESOLVED): a `@given` test that takes the
  function-scoped `dist_name` fixture as a parameter raises
  `HealthCheck.function_scoped_fixture` and fails under the default profile.
  Severity: high if unaddressed. Likelihood: certain if a `@given` test takes
  `dist_name` directly.
  Mitigation: The property test never takes `dist_name` (or any fixture) in its
  `@given` signature. Work item 3 uses the wrapper pattern: a plain (non-`@given`)
  pytest test `test_dist_name_extracts_bare_name_property(dist_name)` resolves the
  function-scoped fixture once, then calls an inner `@given`-decorated body that
  receives the normalizer callable as a plain (non-fixture) argument. The inner
  body's only `@given` parameters are Hypothesis-strategy values, so no
  function-scoped fixture reaches `@given` and the health check cannot fire. No
  `suppress_health_check` is used (suppression would weaken the guard the existing
  `tests/test_contract_properties.py:11-13` convention defends), and no
  session-scoped fixture is relied upon. Verified empirically in-worktree: a
  `@given` test taking `dist_name` raises
  `hypothesis.errors.FailedHealthCheck: ... uses a function-scoped fixture
  'dist_name'`, while the wrapper body (fixture passed as a plain argument)
  passes. (Source: Hypothesis Compatibility docs, "pytest" section, "function-scoped
  fixtures run only once for the entire test, not per-input ... we raise
  `HealthCheck.function_scoped_fixture`",
  <https://hypothesis.readthedocs.io/en/latest/compatibility.html>, title confirms
  "Hypothesis 6.155.7 documentation" matching the locked pin.)
- Risk (B2, determinate, RESOLVED): the property strategy composes a bare name
  with a suffix whose leading character lies inside the PEP 503 name alphabet
  (`[A-Za-z0-9._-]`), so the `_DIST_NAME` regex greedily absorbs it and invariant
  (a) (`normaliser returns exactly the bare name`) is false.
  Severity: high if unaddressed. Likelihood: certain for the original alphabet.
  Mitigation: Work item 3 constrains the suffix so its FIRST character is a true
  delimiter drawn ONLY from `[`, `]`, `<`, `>`, `=`, `~`, `;`, or space — every
  one OUTSIDE `[A-Za-z0-9._-]` — and drops bare version digits, `.`, `_`, and `-`
  from the leading-suffix alphabet. The suffix is generated as
  `delimiter + arbitrary_tail` (or empty). With this constraint the regex stops
  at the delimiter and invariant (a) holds. Verified empirically over 200
  examples with the corrected strategy (all invariants pass); the original alphabet
  reproduced the reviewer's counter-examples (`foo1`->`foo1`, `foo-bar`->`foo-bar`,
  `foo.dev`->`foo.dev`, `foo_x`->`foo_x`). (Source: `tests/test_interrogate_gate.py:24`
  `_DIST_NAME`.)

## Progress

- [x] Work item 1: Lift `dist_name` into `tests/conftest.py` and pin it with
  unit tests in `tests/test_conftest_helpers.py`. Done: added `import re`, the
  module-level `_DIST_NAME` pattern (verbatim from `test_interrogate_gate.py`),
  and a `dist_name` fixture returning a `(spec) -> str | None` callable; added
  parametrized happy-path and unhappy-path unit tests. `make all` green (129
  passed). CodeRabbit raised two minor findings on this execplan only (a
  duplicated Date/Author line and second-person prose); both fixed.
- [x] Work item 2: Migrate `test_contract_test_deps.py` onto the shared
  `pyproject`, `toml_table`, and `dist_name` fixtures; delete `_PYPROJECT`,
  `_dev_dependencies`, and the inline `split`-chain. Done: removed the
  `pathlib`/`tomllib` imports, added `typing`/`collections.abc` for the
  annotated parameters, and rewrote `test_new_test_deps_are_declared_in_dev_group`
  to read the dev group via `toml_table` and match via `dist_name`.
  `make all` green (129 passed); `grep` confirms no `_PYPROJECT` or
  `split(">")` survives. CodeRabbit: 0 findings (one rate-limit retry after a
  ~30s backoff).
- [x] Work item 3: Migrate `test_interrogate_gate.py` onto the `dist_name`
  fixture, delete its private `_DIST_NAME`/`_dist_name`, and add a Hypothesis
  property test for the normalizer invariant using the wrapper pattern (no
  function-scoped fixture in the `@given` signature) with a true-delimiter-led
  suffix strategy. Done: deleted `import re`, `_DIST_NAME`, and `_dist_name`;
  `test_interrogate_is_a_dev_dependency` now consumes `dist_name`; added the
  wrapper-pattern property test asserting (a) bare-name extraction, (b)
  well-formedness, and (c) idempotence. `make all` green (130 passed). Lint
  fixes applied during the deterministic gate: renamed strategy locals to drop
  the leading underscore (RUF052 used-dummy-variable), used `operator.add` in
  place of an addition lambda (FURB118), and split the start/end-alphanumeric
  assertion into two (PT018). `_DIST_NAME` now appears only in
  `tests/conftest.py`. CodeRabbit: 0 findings (one rate-limit retry after a
  ~90s backoff).
- [x] Work item 4: Update `docs/developers-guide.md` §"Shared test
  scaffolding" to record the new `dist_name` fixture and cite audit-1.2.7.
  Done: added `dist_name` to the fixture inventory sentence (described as a
  `(spec) -> str | None` callable reducing a requirement string to its bare
  distribution name) and added `audit-1.2.7.md` (Findings 1-2) to the list of
  discharged audits. `make markdownlint`, `make nixie`, and `make all` all
  green (130 passed). CodeRabbit: 0 findings (several rate-limit retries with
  exponential backoff before the review completed).

## Surprises & discoveries

- Observation (round 2, B1 verification): a `@given` test taking the
  function-scoped `dist_name` fixture as a parameter raises
  `hypothesis.errors.FailedHealthCheck: ... uses a function-scoped fixture
  'dist_name'` under the default profile — confirmed by an isolated probe in the
  worktree. The wrapper pattern (plain outer test resolves the fixture and passes
  the callable into an inner `@given` body as a plain argument) passes cleanly with
  no suppression. This is the same constraint `tests/test_contract_properties.py`
  already encodes.
- Observation (round 2, B2 verification): the original suffix alphabet (which
  included bare version digits, and implicitly any leading `.`/`_`/`-`) falsified
  invariant (a): `foo1`->`foo1`, `foo-bar`->`foo-bar`, `foo.dev`->`foo.dev`,
  `foo_x`->`foo_x` all merge the suffix into the name because `_DIST_NAME`
  greedily continues through `[A-Za-z0-9._-]`. Constraining the suffix's first
  character to a true delimiter outside that set (`[ ] < > = ~ ;` or space) makes
  invariant (a)
  hold over 200 generated examples.

## Decision log

- Decision: Place the property test for the normalizer in
  `tests/test_interrogate_gate.py` rather than `tests/test_conftest_helpers.py`.
  Rationale: `test_conftest_helpers.py` is the focused unit-test home for the
  conftest fixtures and keeps example-based happy/unhappy coverage; the
  Hypothesis property over the normalizer's invariant is a verification
  adversary best colocated with a consumer, and `test_interrogate_gate.py`
  already documents the PEP 508 bare-name intent. Both placements satisfy
  AGENTS.md "Keep pytest tests in the top-level tests/ tree". This is
  revisitable in review; if a reviewer prefers the property live beside the
  fixture, move it to `test_conftest_helpers.py` (same fixture, no behaviour
  change). Date/Author: 2026-06-22, planning agent.
- Decision (resolves round-1 B1): the `@given` property test obtains the
  normalizer via the wrapper pattern, NOT by taking the `dist_name` fixture in its
  `@given` signature. A plain pytest test resolves the function-scoped `dist_name`
  fixture once and calls an inner `@given`-decorated body that receives the
  callable as a plain (non-fixture) argument. Alternatives weighed:
  (1) a session-scoped `dist_name` fixture — rejected: the Hypothesis
  Compatibility docs name only function-scoped fixtures as health-check triggers
  and make no affirmative session-scope exemption guarantee, so session scope is
  more fragile than removing the fixture from the `@given` signature entirely, and
  it would also fork `dist_name` into two scopes; (2) the Wafflecat A4 alternative
  — keep a module-level `_dist_name` function in `conftest.py` and have the fixture
  wrap it, then let the `@given` test reference the module-level callable — rejected:
  it requires the property test to import a private symbol from `conftest`, which
  the developers' guide §"Shared test scaffolding" and AGENTS.md explicitly forbid;
  the wrapper pattern needs no such import; (3) `suppress_health_check` — rejected:
  it weakens the guard the existing `tests/test_contract_properties.py:11-13`
  convention defends. The wrapper pattern is reviewer option 1; it needs no
  conftest import, no health-check suppression, and no session-scope reliance.
  Verified empirically (see Risks B1). Date/Author: 2026-06-22, planning agent.
- Decision (resolves round-1 B2): the property strategy's suffix begins with a
  true delimiter outside the PEP 503 name alphabet — exactly one of
  `[`, `]`, `<`, `>`, `=`, `~`, `;`, or space — generated as
  `delimiter + arbitrary_tail` (or empty). Bare version digits, `.`, `_`, and `-`
  are dropped from the leading-suffix alphabet because the `_DIST_NAME` regex
  treats them as internal name characters and would absorb them, falsifying
  invariant (a). Verified empirically (see Risks B2). Date/Author: 2026-06-22,
  planning agent.
- Decision: Adopt the audit's prescribed mechanism verbatim — a `dist_name`
  fixture returning a `(spec: str) -> str | None` callable backed by the
  `_DIST_NAME` regex — rather than a module-level function or a `staticmethod`.
  Rationale: audit-1.2.7 Finding 2 names this exact shape; the developers' guide
  forbids importing helpers from `conftest`, so a fixture is the sanctioned
  distribution channel; it matches the established callable-returning-fixture
  pattern already used by `read_repo_text` and `toml_table`. Date/Author:
  2026-06-22, planning agent.

## Outcomes & retrospective

Task complete. Both duplications identified by audit-1.2.7 are removed:
`test_contract_test_deps` no longer parses `pyproject.toml` itself (the
`_PYPROJECT` parse and `_dev_dependencies` helper are gone) and the divergent
inline `split`-chain normalizer is gone; the canonical `_DIST_NAME` regex now
lives once, in `tests/conftest.py`, behind the `dist_name` fixture, and both
former owners (`test_interrogate_gate`, `test_contract_test_deps`) consume it by
fixture name. Guard semantics are preserved: the migrated interrogate-gate
assertion behaves identically, the two version-pin tests are untouched, and a
Hypothesis property test pins the normalizer invariant (bare-name extraction,
well-formedness, idempotence). `make all` is green at HEAD (130 passed),
markdownlint and nixie are clean.

Deviations from the plan, with rationale:

- `make fmt` runs `mdformat-all` over every Markdown file and rewrapped ~30
  unrelated docs. The aggregate `make all` gate uses `check-fmt`, which does
  not check Markdown, so this churn is not required. The unrelated reformatting
  was stashed away (matching the precedent set by prior work items, which
  carried identical stashes), keeping each commit scoped to its work item. Only
  Python formatting from `make fmt` was retained.
- Work item 1's CodeRabbit pass surfaced two minor findings on this execplan
  itself (a duplicated Date/Author line and second-person prose); both were
  fixed in the same commit. A round-1 review artefact
  (`roadmap-1-2-11.review-r1.md`) carried a pre-existing MD013 over-long line;
  it was wrapped so `make markdownlint` stays green, then committed alongside
  work item 1.
- The plan's illustrative property-test snippet used underscore-prefixed
  strategy locals and an addition lambda; Ruff (RUF052 used-dummy-variable,
  FURB118 reimplemented-operator) and Pylint (PT018 composite assertion)
  required renaming the locals, switching to `operator.add`, and splitting the
  start/end-alphanumeric assertion in two. These are surface adjustments; the
  strategy and invariants are exactly as planned.

Footprint: four commits across `tests/conftest.py`,
`tests/test_conftest_helpers.py`, `tests/test_contract_test_deps.py`,
`tests/test_interrogate_gate.py`, and `docs/developers-guide.md` — five source
files, within the five-file Tolerance.

## Context and orientation

The reader needs no prior plan. The relevant files, by full worktree-relative
path:

- [`tests/conftest.py`](../../tests/conftest.py) — the single home for shared
  test scaffolding, each helper exposed as a pytest fixture. Already provides
  `project_root`, `pyproject`, `read_repo_text`, `toml_table`,
  `single_program_catalogue`, and `venv_scripts_dir`. Fixtures that return
  callables (`read_repo_text`, `toml_table`) are the template for the new
  `dist_name`. This file is gated as production code: full docstrings, no bare
  `assert`.
- [`tests/test_contract_test_deps.py`](../../tests/test_contract_test_deps.py) —
  pins the two test-only dev dependencies (`hypothesis`, `syrupy`). It currently
  carries `_PYPROJECT` (line 30) and `_dev_dependencies` (lines 33-42), and the
  inline normalizer `spec.split()[0].split(">")[0].split("=")[0]` (line 79).
- [`tests/test_interrogate_gate.py`](../../tests/test_interrogate_gate.py) —
  guards the `interrogate` docstring-coverage gate. It already consumes the
  `pyproject`, `toml_table`, and `read_repo_text` fixtures, and owns the
  canonical `_DIST_NAME` regex (line 24) and `_dist_name` helper (lines 27-30),
  used at line 75 to assert `interrogate` is a declared dev dependency.
- [`tests/test_conftest_helpers.py`](../../tests/test_conftest_helpers.py) — the
  focused unit-test suite for the conftest fixtures. New `dist_name` unit tests
  land here, following the existing happy/unhappy-path pattern (e.g.
  `test_toml_table_returns_the_sub_table` / `test_toml_table_rejects_a_non_table`).
- [`docs/developers-guide.md`](../../docs/developers-guide.md) §"Shared test
  scaffolding" (lines 20-47) — the prose convention listing every shared
  fixture. It must gain `dist_name` and cite audit-1.2.7.
- [`docs/issues/audit-1.2.7.md`](../issues/audit-1.2.7.md) Findings 1-2 — the
  authority for this task's scope and prescribed fixes.

Terms of art, defined:

- "PEP 508 requirement string" / "dependency specifier": the string form of a
  package requirement, e.g. `hypothesis[cli]>=6.0; python_version >= "3.10"`. The
  leading run before any extras bracket, version operator, marker, or whitespace
  is the "bare distribution name".
- "Normalizer": a function reducing a specifier to its bare distribution name.
  The canonical one here is the `_DIST_NAME` regex
  `^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?`, which matches a name that
  starts and ends with an alphanumeric and may contain `.`, `_`, or `-`
  internally, stopping at the first character outside that set.
- "Fixture": a pytest-provided value or callable injected into a test by
  parameter name; the only sanctioned way to share `conftest` scaffolding here.

Verified library facts the plan relies on (cited, not asserted from memory):

- The locked normalizer semantics were verified empirically in the worktree
  against the weak `split`-chain. Inputs and outputs (regex vs. weak chain):
  `hypothesis[cli]>=6.0` -> `hypothesis` vs. `hypothesis[cli]`;
  `interrogate[toml]` -> `interrogate` vs. `interrogate[toml]`;
  `pkg<2.0` -> `pkg` vs. `pkg<2.0`;
  `foo; python_version>="3.10"` -> `foo` vs. `foo;`. These confirm the
  divergence audit-1.2.7 Finding 2 describes and seed the property/parametrized
  test cases. (Source: `tests/test_interrogate_gate.py:24` `_DIST_NAME`;
  `tests/test_contract_test_deps.py:79`.)
- `cuprum` is locked at `0.1.0` (`uv.lock`, `name = "cuprum"`). This task adds NO
  cuprum API surface: the migrated tests parse TOML and normalize strings; they
  do not construct a `ProgramCatalogue`, allowlist a `Program`, or run any
  command. The existing cuprum usage in `tests/conftest.py`
  (`ProgramCatalogue`, `ProjectSettings`) and `tests/test_conftest_helpers.py`
  (`sh.make`, `Program`) is untouched, so no cuprum behaviour needs re-pinning
  for this change. (Source: `tests/conftest.py:27,113-141`;
  `tests/test_conftest_helpers.py:74-108`.)
- `hypothesis` is a locked dev dependency at `6.155.7` (`pyproject.toml:28`,
  `tests/test_contract_test_deps.py:27`). The property test in work item 3 uses
  the already-available `hypothesis.given` / `hypothesis.strategies`; no new
  dependency is introduced.
- Hypothesis raises `HealthCheck.function_scoped_fixture` when a `@given` test
  takes a function-scoped pytest fixture, because such a fixture "run[s] only once
  for the entire test, not per-input". The check fires under the default profile
  unless suppressed via `settings.suppress_health_check`. The documentation names
  only function-scoped fixtures as the trigger and makes no affirmative exemption
  guarantee for session-scoped fixtures. (Source: Hypothesis Compatibility docs,
  "Testing frameworks → pytest",
  <https://hypothesis.readthedocs.io/en/latest/compatibility.html>; the page title
  reads "Compatibility - Hypothesis 6.155.7 documentation", matching the locked
  pin.) Confirmed empirically in-worktree: a `@given` test taking `dist_name`
  raises `hypothesis.errors.FailedHealthCheck: ... uses a function-scoped fixture
  'dist_name'`; the wrapper pattern (function-scoped fixture resolved by a plain
  outer test and passed into an inner `@given` body as a plain argument) does not
  trip the check and passes. This is the precedent already encoded at
  `tests/test_contract_properties.py:11-13`.
- `make all` runs `build check-fmt lint typecheck test` (`Makefile:28`).
  `make test` runs `pytest -v -n auto` under xdist (`Makefile:116`,
  `PYTEST_XDIST_WORKERS ?= auto`). `make markdownlint` runs `markdownlint-cli2`
  over `**/*.md` (`Makefile:108-109`); `make nixie` validates Mermaid
  (`Makefile:111-113`). The developers-guide edit is the only Markdown change,
  so its work item runs `make markdownlint` and `make nixie` in addition to
  `make all`.

## Plan of work

Four ordered, independently committable, gate-passable work items. Each ends
with `make all`; the documentation item additionally runs `make markdownlint`
and `make nixie`. Commit after each item, gating the commit on the full
aggregate gate per AGENTS.md.

### Work item 1 — Add the `dist_name` fixture to `tests/conftest.py` with unit tests

Implements: audit-1.2.7 Finding 2 (centralize the normalizer); developers' guide
§"Shared test scaffolding" (new shared scaffolding belongs in `conftest` as a
fixture); AGENTS.md "Python verification and testing" (consume by fixture name,
cover happy and unhappy paths).

Docs to read first: `docs/issues/audit-1.2.7.md` Finding 2;
`docs/developers-guide.md` §"Shared test scaffolding";
`tests/conftest.py` (the `read_repo_text` and `toml_table` callable-fixture
pattern).

Skills to load: `leta` (navigate `tests/conftest.py` and the
`_DIST_NAME`/`_dist_name` definitions); `python-router` then `python-testing`
(fixture design, parametrization); `en-gb-oxendict` (docstring/comment prose).

Edits:

1. In `tests/conftest.py`, add `import re` (top-level, alongside the existing
   stdlib imports) and a module-level compiled pattern lifted verbatim from
   `test_interrogate_gate.py`:
   `_DIST_NAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?")`,
   with the same explanatory comment.
2. Add a `dist_name` fixture returning a
   `cabc.Callable[[str], str | None]` callable. Because `conftest.py` is gated
   as production code, the fixture carries a full Numpy-style docstring (matching
   the existing fixtures), and the inner `_normalise` callable carries a
   one-line docstring. The callable mirrors `_dist_name` exactly: strip the
   spec, match `_DIST_NAME`, return `match.group(0)` or `None`. No bare
   `assert`; it raises nothing.
3. In `tests/test_conftest_helpers.py`, add parametrized unit tests for the
   `dist_name` fixture: a happy-path `@pytest.mark.parametrize` over the verified
   cases (`hypothesis` -> `hypothesis`, `hypothesis[cli]>=6.0` -> `hypothesis`,
   `interrogate[toml]` -> `interrogate`, `pkg<2.0` -> `pkg`,
   `syrupy ~= 5.3` -> `syrupy`, `foo; python_version>="3.10"` -> `foo`), and an
   unhappy-path case asserting an empty or non-name-leading input (e.g. `"  "`
   or `">=1.0"`) returns `None`.

Tests this item adds (AGENTS.md testing rules — unit, happy and unhappy paths):

- `tests/test_conftest_helpers.py::test_dist_name_extracts_bare_name`
  (parametrized happy path over the six verified specifiers).
- `tests/test_conftest_helpers.py::test_dist_name_returns_none_for_non_name`
  (unhappy path).

Validation: `make all`. Expect the new tests to pass and the existing suite to
stay green. (The fixture is unused by production modules until work items 2-3,
so this item is independently green.)

### Work item 2 — Migrate `test_contract_test_deps.py` onto the shared fixtures

Implements: audit-1.2.7 Finding 1 (remove the seventh `pyproject` parse) and
Finding 2 (drop the weaker inline normalizer); developers' guide §"Shared test
scaffolding" (consume by fixture name, no per-module parse).

Docs to read first: `docs/issues/audit-1.2.7.md` Findings 1-2;
`tests/test_interrogate_gate.py::test_interrogate_is_a_dev_dependency` (the
target shape — read the dev group via
`toml_table(pyproject, "dependency-groups")["dev"]` and filter with the
normalizer).

Skills to load: `leta` (refs to `_PYPROJECT`/`_dev_dependencies` to confirm no
other caller); `python-router` then `python-testing`; `en-gb-oxendict`.

Edits to `tests/test_contract_test_deps.py`:

1. Delete `_PYPROJECT` (line 30) and `_dev_dependencies` (lines 33-42). Delete
   the now-unused imports `pathlib` and `tomllib` (keep `importlib.metadata`
   and `hypothesis`, still used by the version-pin tests).
2. Rewrite `test_new_test_deps_are_declared_in_dev_group` to take the
   `pyproject`, `toml_table`, and `dist_name` fixtures as parameters, ANNOTATED
   to match `test_interrogate_gate.py`'s call site exactly: `pyproject:
   dict[str, object]`, `toml_table: cabc.Callable[[cabc.Mapping[str, object],
   str], dict[str, object]]`, and `dist_name: cabc.Callable[[str], str | None]`.
   Read the dev group as `dev = toml_table(pyproject, "dependency-groups")["dev"]`,
   assert it is a `list`, then assert `hypothesis` and `syrupy` are each present
   by `any(isinstance(spec, str) and dist_name(spec) == "<name>" for spec in dev)`.
   This replaces the `split`-chain with the regex normalizer and removes the
   per-module parse.
3. Leave `test_hypothesis_import_and_version` and `test_syrupy_version`
   unchanged — they read installed distribution metadata, not `pyproject.toml`
   (audit-1.2.7 Finding 1 explicitly excludes them). Update the module docstring
   only if it references the removed helpers.
4. (Resolves round-1 advisory A1.) Because the migrated test's parameters ARE
   annotated (edit 2), the type-only imports are genuinely needed and must be
   added: `import typing as typ` (top level) and, under
   `if typ.TYPE_CHECKING:`, `import collections.abc as cabc`, following the
   established pattern in `test_interrogate_gate.py:17-20`. These imports are
   used by the annotations, so Ruff F401 will not fire. (If, contrary to this
   plan, the implementer chooses to leave the params unannotated, they must NOT
   add these imports — but the plan's decision is to annotate, for consistency
   with the existing `test_interrogate_gate.py` call site.)

Tests this item updates: `test_new_test_deps_are_declared_in_dev_group` (same
two guarantees — `hypothesis` and `syrupy` declared in `[dependency-groups].dev`
— now expressed through the shared normalizer). No new behaviour; the assertion
strengthens to handle extras/markers without changing what passes today.

Validation: `make all`. The three `test_contract_test_deps` tests pass.
Confirm the duplications are gone: `grep -n "_PYPROJECT\|split(\">\")"
tests/test_contract_test_deps.py` returns nothing.

### Work item 3 — Migrate `test_interrogate_gate.py` onto `dist_name` and add a property test

Implements: audit-1.2.7 Finding 2 (single normalizer, both consumers on it);
AGENTS.md "Use property tests with hypothesis … when a change introduces an
invariant over a range of inputs".

Docs to read first: `docs/issues/audit-1.2.7.md` Finding 2;
`tests/test_interrogate_gate.py` (current `_DIST_NAME`/`_dist_name` and the
`test_interrogate_is_a_dev_dependency` call site);
`tests/test_contract_properties.py:11-13` (the repo's load-bearing convention:
"no `@given` test takes a function-scoped fixture"; the wrapper pattern in this
work item exists to honour it); the Hypothesis Compatibility docs "Testing
frameworks → pytest" section
(<https://hypothesis.readthedocs.io/en/latest/compatibility.html>), which states
function-scoped fixtures run once per test and trigger
`HealthCheck.function_scoped_fixture`.

Skills to load: `leta` (confirm `_dist_name` has no caller beyond this module);
`python-router` then `python-verification` (confirm Hypothesis is the right
adversary for a pure normalizer invariant) then `hypothesis` (strategy design,
the filtering trap, `@given` usage, and the function-scoped-fixture health check);
`en-gb-oxendict`.

Edits to `tests/test_interrogate_gate.py`:

1. Delete the module-level `_DIST_NAME` regex (line 24), the `_dist_name`
   function (lines 27-30), and the now-unused `import re`. The pattern now lives
   only in `tests/conftest.py`.
2. Add `dist_name` as a parameter to `test_interrogate_is_a_dev_dependency` and
   replace the `_dist_name(spec)` call with `dist_name(spec)`. Behaviour is
   identical; the source moves to the shared fixture.
3. Add a Hypothesis property test for the normalizer invariant, structured with
   the WRAPPER PATTERN so no function-scoped fixture reaches `@given` (resolves
   round-1 B1). Concretely:

   - Define a plain (non-`@given`) pytest test
     `test_dist_name_extracts_bare_name_property(self, dist_name)` that takes the
     function-scoped `dist_name` fixture as an ordinary parameter and immediately
     calls an inner `@given`-decorated body, passing the resolved callable in as
     a plain argument. The OUTER test is not decorated with `@given`; the INNER
     body IS, and its only `@given` parameters are Hypothesis-strategy values
     (`name`, `suffix`). The normalizer arrives as a closure variable / plain
     argument, never as a fixture in the `@given` signature, so
     `HealthCheck.function_scoped_fixture` cannot fire (verified empirically; see
     Risks B1 and the Hypothesis Compatibility citation). Do NOT use
     `suppress_health_check` and do NOT introduce a session-scoped fixture.
   - Strategy (resolves round-1 B2). Build the bare name directly (no filtering):
     `name = leading_alnum + internal + trailing_alnum`, where `leading_alnum`
     and `trailing_alnum` are `st.sampled_from` an alphanumeric set and
     `internal` is `st.text` over the PEP 503 internal alphabet `[A-Za-z0-9._-]`
     (so the name may contain `.`/`_`/`-` internally but starts and ends
     alphanumeric), bounded
     (e.g. `max_size=8`). Build the suffix as EITHER the empty string OR
     `delimiter + tail`, where `delimiter` is `st.sampled_from` the TRUE-delimiter
     set `["[", "]", "<", ">", "=", "~", ";", " "]` — every character OUTSIDE
     `[A-Za-z0-9._-]` — and `tail` is bounded `st.text` over an extras/operator/
     marker/digit alphabet. CRITICAL: the suffix's first character MUST be a true
     delimiter; bare version digits, `.`, `_`, and `-` are EXCLUDED as the leading
     suffix character because the `_DIST_NAME` regex would absorb them into the
     name and falsify invariant (a). The composed specifier is `name + suffix`.
   - Assert, inside the inner body, with `normalise = dist_name`:
     (a) `normalise(name + suffix) == name` (exact bare-name extraction);
     (b) well-formedness of the result `got = normalise(name + suffix)`: `got`
     contains no character outside `[A-Za-z0-9._-]` and neither starts nor ends
     with `.`/`_`/`-` (here `got` is never `None` because `name` always begins
     with an alphanumeric, so a match is guaranteed);
     (c) idempotence on the non-`None` branch: `normalise(got) == got`. Because
     every composed specifier here has a valid leading name, `got` is non-`None`
     by construction, so the second pass never calls `.strip()` on `None`
     (resolves round-1 advisory A2 — the idempotence property is scoped to the
     valid-leading-name branch and the strategy guarantees it; no `assume`/filter
     on `None` is needed since `None` cannot arise, but the body must NOT call
     `normalise(None)`).
   - Keep the strategy bounded and deterministic (default Hypothesis settings;
     bounded text alphabets; no external state) so it stays well within the
     `timeout = 30` ceiling under `-n auto` (advisory A3; precedent:
     `tests/test_contract_properties.py`).

Tests this item adds/updates:

- Updated: `test_interrogate_is_a_dev_dependency` (now consumes `dist_name`).
- Added (property, Hypothesis, wrapper pattern):
  `tests/test_interrogate_gate.py::TestInterrogateGate::test_dist_name_extracts_bare_name_property`
  — a plain pytest test taking the `dist_name` fixture that drives an inner
  `@given` body (no fixture in the `@given` signature) asserting invariants
  (a) bare-name extraction, (b) well-formedness, and (c) idempotence over
  generated specifiers whose suffix begins with a true delimiter.

Validation: `make all`. Expect the interrogate guard tests to pass and the new
property test to pass. Confirm `grep -n "_dist_name\|_DIST_NAME"
tests/test_interrogate_gate.py` returns nothing.

### Work item 4 — Record the `dist_name` fixture in the developers' guide

Implements: AGENTS.md "When code changes alter behaviour … update the relevant
file(s) in the docs/ directory"; developers' guide §"Shared test scaffolding"
keeps the fixture inventory authoritative.

Docs to read first: `docs/developers-guide.md` §"Shared test scaffolding"
(lines 20-47); `docs/documentation-style-guide.md` (wrap prose at 80 columns);
`docs/issues/audit-1.2.7.md` (for the citation).

Skills to load: `leta` (navigate the guide); `en-gb-oxendict` (Oxford spelling,
80-column wrap).

Edits to `docs/developers-guide.md`:

1. In the §"Shared test scaffolding" fixture inventory (the sentence beginning
   "It exposes …", lines 22-27), add the `dist_name` fixture: "and the PEP 508
   dependency-name normalizer (`dist_name`)", describing it as returning a
   `(spec) -> str | None` callable that reduces a requirement string to its bare
   distribution name.
2. Add `audit-1.2.7.md` to the list of audits this consolidation discharges
   (lines 41-47), since this task closes its Findings 1-2.
3. Keep paragraphs wrapped at 80 columns; do not wrap inline code or headings.

Tests this item adds: none (documentation only). The convention is already
enforced by `test_conftest_helpers.py` (the fixture exists and works) and the
two migrated consumers.

Validation: `make markdownlint` and `make nixie` (Markdown changed), then
`make all` to confirm the suite remains green. Expect markdownlint to report no
errors and nixie to find no Mermaid regressions (the section has no diagrams).

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-11`. Use full
paths; the agent's cwd resets between shell calls.

1. Confirm the branch: `git -C <worktree> branch --show-current` -> expect
   `roadmap-1-2-11`.
2. Work item 1: edit `tests/conftest.py` and `tests/test_conftest_helpers.py`;
   run `make all`. Expected tail: pytest reports all tests passed (the new
   `dist_name` tests included). Commit.
3. Work item 2: edit `tests/test_contract_test_deps.py`; run `make all`. Expect
   the three module tests green and Ruff clean (no F401 from removed imports).
   Commit.
4. Work item 3: edit `tests/test_interrogate_gate.py`; run `make all`. Expect
   the interrogate guard tests and the new property test green. Commit.
5. Work item 4: edit `docs/developers-guide.md`; run `make markdownlint`,
   `make nixie`, then `make all`. Expect no markdownlint or nixie errors and a
   green suite. Commit.

Expected transcript shape for each `make all` (abbreviated):

```plaintext
$ make all
... ruff format --check ... ok
... ruff check ... interrogate ... pylint ... ok
... ty check ... ok
... pytest -v -n auto ... N passed
```

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes; `tests/test_contract_test_deps.py` (3 tests),
  `tests/test_interrogate_gate.py` (3 class tests + 1 property test), and the new
  `tests/test_conftest_helpers.py` `dist_name` unit tests all pass. Each new or
  changed test fails before its work item's edit and passes after (red/green):
  for work item 2, temporarily reverting to the `split`-chain and feeding a
  `hypothesis[cli]>=6.0`-style spec demonstrates the old assertion would fail
  where the new one passes.
- Lint/typecheck: `make lint` (Ruff, `interrogate` 100%, Pylint) and
  `make typecheck` (`ty`) pass with no new findings. No bare `assert` in
  `tests/conftest.py`; full docstrings on the new fixture and its inner
  callable.
- Duplication removed: `grep -rn "_PYPROJECT\|_dev_dependencies\|split(\">\")"
  tests/test_contract_test_deps.py` and
  `grep -n "_DIST_NAME\|_dist_name" tests/test_interrogate_gate.py` both return
  nothing; `_DIST_NAME` appears only in `tests/conftest.py`.
- Markdown: `make markdownlint` and `make nixie` pass after the developers-guide
  edit.

Quality method (how we check): run `make all` after every work item, plus
`make markdownlint` and `make nixie` for work item 4. The aggregate gate is the
acceptance authority per AGENTS.md.

## Idempotence and recovery

Every step is a re-runnable text edit gated by `make all`. If a `make all` run
fails, fix forward and re-run; nothing is destructive. If a work item's edit
proves wrong, `git checkout -- <file>` restores it from the last commit and the
item can be retried, since each item is committed independently. No state files,
migrations, or external services are touched.

## Artefacts and notes

The load-bearing divergence proof (verified in-worktree), seeding the
parametrized and property cases:

```plaintext
spec                          regex       weak split-chain
'hypothesis[cli]>=6.0'        hypothesis  hypothesis[cli]
'interrogate[toml]'           interrogate interrogate[toml]
'pkg<2.0'                     pkg         pkg<2.0
'foo; python_version>="3.10"' foo         foo;
'syrupy ~= 5.3'               syrupy      syrupy
```

## Interfaces and dependencies

Use these exact names and shapes at the end of the task:

- In `tests/conftest.py`, a module-level `_DIST_NAME` compiled from
  `r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"` and a fixture:

```python
@pytest.fixture
def dist_name() -> cabc.Callable[[str], str | None]:
    """Return a PEP 508 bare-distribution-name normaliser."""

    def _normalise(spec: str) -> str | None:
        """Return the bare distribution name of ``spec`` or ``None``."""
        match = _DIST_NAME.match(spec.strip())
        return match.group(0) if match else None

    return _normalise
```

- `tests/test_contract_test_deps.py::test_new_test_deps_are_declared_in_dev_group`
  takes `(pyproject, toml_table, dist_name)` and asserts presence via
  `dist_name`.
- `tests/test_interrogate_gate.py::TestInterrogateGate.test_interrogate_is_a_dev_dependency`
  takes `(pyproject, toml_table, dist_name)`; the module no longer defines
  `_DIST_NAME` or `_dist_name`.
- `tests/test_interrogate_gate.py` gains `from hypothesis import given`,
  `from hypothesis import strategies as st`, and the wrapper-pattern property
  test. The outer test takes `dist_name` (a function-scoped fixture); the inner
  `@given` body takes ONLY strategy values and receives the normalizer as a plain
  argument. `test_interrogate_gate.py` IS matched by the `**/test_*.py`
  `per-file-ignores` glob (`pyproject.toml:96`), so bare `assert` (S101) and
  `PLR6301` are permitted here — unlike `conftest.py`. However, `interrogate`
  (`pyproject.toml:307`, `fail-under = 100`) runs over all of `PYTHON_TARGETS`
  including `tests/`, so BOTH the outer test AND the inner `_check` body MUST
  carry a docstring (the existing `tests/test_contract_properties.py` nested
  helpers `_build_app`/`_drive` are the precedent). Shape (illustrative; the inner
  `_check` docstring is shown, strategy var docstrings are not required because
  they are assignments, not defs):

```python
def test_dist_name_extracts_bare_name_property(
    self,
    dist_name: cabc.Callable[[str], str | None],
) -> None:
    """Property: dist_name extracts exactly the bare PEP 508 name."""
    _leading = st.sampled_from("abcXYZ012")
    _internal = st.text(alphabet="abcXYZ012._-", max_size=8)
    name = st.builds(lambda a, m, z: a + m + z, _leading, _internal, _leading)
    _delim = st.sampled_from(["[", "]", "<", ">", "=", "~", ";", " "])
    _tail = st.text(alphabet="abc012[]<>=~;. _-", max_size=8)
    suffix = st.one_of(st.just(""), st.builds(lambda d, t: d + t, _delim, _tail))

    @given(name=name, suffix=suffix)
    def _check(name: str, suffix: str) -> None:
        """Assert the bare-name, well-formedness, and idempotence invariants."""
        got = dist_name(name + suffix)
        assert got == name                       # (a) exact bare name
        assert got is not None                   # guaranteed by construction
        assert all(c.isalnum() or c in "._-" for c in got)  # (b)
        assert got[0].isalnum() and got[-1].isalnum()       # (b)
        assert dist_name(got) == got             # (c) idempotence, non-None

    _check()
```

  The `@given` signature contains no fixture, so
  `HealthCheck.function_scoped_fixture` does not fire (verified; Risks B1).

- No new external dependency. `hypothesis` (locked `6.155.7`) supplies `@given`
  and `strategies` for the property test. `cuprum` (locked `0.1.0`) is not used
  by any code this task touches.
