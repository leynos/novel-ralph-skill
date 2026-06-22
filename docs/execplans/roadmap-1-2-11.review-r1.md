# Logisphere design review — roadmap 1.2.11 — Round 1

Verdict: REVISE. The plan is well-grounded on its refactor core (Findings 1 and
2 of audit-1.2.7), and its TOML-migration work items (1, 2, 4) are atomic,
ordered, testable, and design-conformant. The Hypothesis property test in Work
item 3,
however, contradicts an established, documented repo convention and specifies an
invariant that is false for the strategy it describes. Two blocking defects must
be fixed before implementation.

Verification performed (sources cited so the trail is reproducible):

- Regex normaliser behaviour confirmed empirically in-worktree against the plan's
  table; all six cited cases reproduce exactly. (`tests/test_interrogate_gate.py:24`.)
- pyproject Ruff `per-file-ignores` glob `**/test_*.py` confirmed at line 96;
  `[tool.interrogate] fail-under = 100` at 312; `tool.pytest.ini_options`
  `timeout = 30` at 325; `pytest-timeout` + `pytest-xdist` are locked dev deps.
- Makefile `all` (line 28), `test` under `-n auto` (115-116), `interrogate` over
  `$(PYTHON_TARGETS)` (96), `PYTHON_TARGETS = novel_ralph_skill tests` (15).
- developers-guide §"Shared test scaffolding" lines 20-47 confirmed; the audit
  citation list to extend is at 41-47.
- conftest fixture patterns (`read_repo_text`, `toml_table`) confirmed as the
  callable-returning-fixture template.
- An existing Hypothesis property suite already lives at
  `tests/test_contract_properties.py`; it is the precedent the new property test
  must follow, and it is the source of blocking defect B1.

## Blocking defects (back to the planner)

### B1 (Doggylump / Telefono) — Property test will trip `HealthCheck.function_scoped_fixture`

`tests/test_contract_properties.py:11-13` records the load-bearing repo
convention verbatim: "All Hypothesis inputs come from strategies; no `@given`
test takes a function-scoped fixture, which would raise
`HealthCheck.function_scoped_fixture` (Hypothesis Compatibility docs)."

Work item 3 specifies a `@given` property test for the normaliser, but the plan
deletes `_DIST_NAME`/`_dist_name` from `test_interrogate_gate.py` and places the
normaliser ONLY in `tests/conftest.py`, reachable solely as the function-scoped
`dist_name` fixture (Constraints; Work item 3 edit 1; Interfaces lines 505-526).
The only sanctioned way for the property test to obtain the normaliser is then to
take `dist_name` as a parameter — which, combined with `@given` and the plan's
stated "default Hypothesis settings" (Risks, line 118), is a guaranteed
`HealthCheck.function_scoped_fixture` failure, not a hypothetical. The plan's
xdist-flakiness risk (lines 116-121) does not cover this; it is a determinate
error under the default profile.

The plan must specify HOW the `@given` test reaches a fixture-free normaliser
without re-introducing the duplication this task exists to remove, and without
suppressing the health check (suppression would weaken the guard the existing
convention defends). Options for the planner to choose and pin explicitly (do not
leave to the implementer):

- Resolve the fixture once via a non-`@given` wrapper test that calls the
  property body, passing the callable in as a plain argument (the body itself
  takes no fixture); or
- Have the `dist_name` fixture's underlying callable be a module-level function
  in `conftest.py` that the fixture merely returns, and let the property test in
  `test_interrogate_gate.py` import nothing from conftest but instead exercise the
  normaliser through a session-scoped fixture (session scope does not trip the
  health check) — but verify session scope against the Hypothesis compatibility
  docs and cite it; or
- Place the property test in `tests/test_conftest_helpers.py` or
  `test_interrogate_gate.py` and request `dist_name` via a `@pytest.fixture` of
  `scope="session"`, then cite the Hypothesis docs confirming session-scoped
  fixtures are exempt.

Whichever path is chosen, the plan must cite the Hypothesis "Compatibility /
function-scoped fixtures" documentation (firecrawl the official page) rather than
assert the behaviour from memory, because the existing test already pays this
cost and the new one must match.

### B2 (Telefono / Pandalump) — Property-test invariant (a) is false for the stated strategy

Work item 3 edit 3 builds the specifier by composing "a valid bare name ... with
an optional suffix drawn from extras/operator/marker characters (`[`, `]`, `>`,
`<`, `=`, `~`, `;`, space, version digits)" and asserts invariant (a): "the
normaliser returns exactly the bare name for the composed specifier."

This is false. The PEP 503 name alphabet the regex accepts internally includes
`.`, `_`, and `-`, and the suffix alphabet the plan names includes "version
digits". Empirically in-worktree:

```text
'foo1'    -> 'foo1'    (suffix = bare digit; absorbed)     invariant (a) FAILS
'foo-bar' -> 'foo-bar' (a '-'-led suffix is a valid name)  invariant (a) FAILS
'foo.dev' -> 'foo.dev'                                       invariant (a) FAILS
'foo_x'   -> 'foo_x'                                         invariant (a) FAILS
```

The regex greedily continues through `[A-Za-z0-9._-]`, so any composed suffix
beginning with a digit, `.`, `_`, or `-` merges into the name and the bare-name
equality breaks. The strategy must guarantee the suffix begins with a true
delimiter — a character OUTSIDE `[A-Za-z0-9._-]`, i.e. one of `[ < > = ~ ;` or a
space — and must drop bare "version digits" from the leading-suffix alphabet.
Equivalently, generate the suffix as `delimiter + arbitrary tail`. As written the
plan either fails spuriously or forces the implementer to silently redesign the
strategy, diverging from the plan. Specify the corrected strategy precisely (the
suffix's first character set) so the implementation is mechanical.

## Advisory (non-blocking, address if cheap)

- A1 (Pandalump) — Work item 2 edit 4 says add
  `if typ.TYPE_CHECKING: import collections.abc as cabc` "following
  test_interrogate_gate.py", but the Interfaces section (lines 521-523) shows the
  migrated function's params without annotations, and the existing contract-test
  functions are unannotated module-level functions. If the migrated params are
  annotated, `cabc` (and `typ`) are needed; if not, adding the import is an unused
  import (Ruff F401). Resolve the inconsistency: either annotate the params (and
  import `cabc`/`typ`) or do not add the import. State which.

- A2 (Telefono) — Invariant (c) idempotence
  `dist_name(dist_name(spec)) == dist_name(spec)` is sound (the regex cannot emit
  a name ending in `.`/`_`/`-`, so a second pass is stable), but it only holds for
  specifiers with a valid leading name; for `dist_name(spec) is None` the inner
  call raises `AttributeError` on `None.strip()`. The plan already scopes (c) to
  "specifiers with a valid leading name", so guard the property accordingly
  (assume/filter on the non-None branch) and say so explicitly to avoid a
  `None`-strip crash during shrinking.

- A3 (Buzzy Bee) — The `timeout = 30` pytest-timeout ceiling under `-n auto`
  applies to the new property test. The plan's pure/fast reasoning is correct and
  the existing `test_contract_properties.py` already coexists with this ceiling,
  so this is not blocking; but the plan should note the existing precedent rather
  than reason from first principles, since that precedent is also the source of
  B1.

- A4 (Wafflecat) — Strongest alternative: keep the normaliser as a module-level
  function in `conftest.py` AND expose it as a fixture wrapping that function.
  Tests that are not `@given` consume the fixture (honouring the no-conftest-import
  rule for ordinary tests); the single `@given` property test, which structurally
  cannot consume a function-scoped fixture, references the module-level callable.
  This trades a one-line, documented exception to the import rule for a property
  test that needs no health-check suppression and no session-fixture gymnastics.
  It is a credible structural alternative to B1's options and the planner should
  weigh it explicitly; whichever is chosen, the developers-guide note in Work
  item 4 must record the exception so the convention stays honest.

## What is sound (so the planner does not over-correct)

- Scope, ordering, and atomicity of Work items 1, 2, 4 are correct; each is
  independently committable and gate-passable.
- The deterministic/judgemental boundary (ADR-001) is untouched; no cuprum API
  surface is added; the two version-pin tripwires are correctly left alone.
- The `dist_name` fixture shape `(spec: str) -> str | None`, the verbatim
  `_DIST_NAME` lift, and the docstring/no-bare-assert constraints for
  `conftest.py` are all correct against the gates.
- The duplication-removal greps and red/green demonstration for Work item 2 are
  well specified.
