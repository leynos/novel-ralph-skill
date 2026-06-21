# Logisphere design review — ExecPlan roadmap-1-2-4 (round 1)

Reviewer: adversarial Logisphere crew (Pandalump, Wafflecat, Buzzy Bee,
Telefono, Doggylump, Dinolump) plus pre-mortem and alternatives checkpoint.
Date: 2026-06-22. Verdict: **Proceed with conditions** (no blocking defects).

## What was verified against ground truth

Every load-bearing claim in the plan was checked against the real files, not the
planner's summary:

- `novel_ralph_skill/commands/stub.py` — five named module-level `def`s, each
  calling `make_stub_app("<name>")()` with the console-script name inline, plus
  `STUB_EXIT_CODE = 2` and the `make_stub_app` factory. Matches the plan.
- `pyproject.toml` `[project.scripts]` (five entries → `…stub:<func>`),
  `requires-python = ">=3.14"`, `[build-system]` = hatchling. Matches.
- `tests/test_command_stubs.py` (`COMMAND_NAMES`, `ENTRY_POINTS`),
  `tests/test_console_scripts_e2e.py` (a second `COMMAND_NAMES`, POSIX skip,
  `slow`, cuprum run-loop), `tests/test_pyproject_scripts.py` (`tomllib` +
  `EXPECTED_SCRIPTS`). All present and as described.
- cuprum API at the sibling checkout: `Program = typ.NewType("Program", str)`
  (`program.py`), `ProgramCatalogue`/`ProjectSettings` (`catalogue.py`),
  `make`/`SafeCmd.run_sync`/`CommandResult` (`sh.py`). All exist; the plan's
  re-pin is accurate.
- ADR-005 fixes exactly the five names; ADR-004 fixes console-script
  distribution; ADR-001 deterministic/judgemental boundary is respected (pure
  packaging, no judgemental content); ADR-003 JSON envelope correctly deferred
  to step 1.3.
- Makefile: `all = build check-fmt lint typecheck test`; `test = pytest -v -n
  auto`; `lint-python` runs Ruff + `interrogate --fail-under 100` + PyPy Pylint;
  `typecheck = ty check`. Matches the plan's descriptions.
- `.rules/python-{00,typing,return,pyproject}.md` all exist.

No uncited memory-based claim about a locked library was found. The plan relies
only on `tomllib` order preservation (stdlib, documented) and hatchling reading
`[project.scripts]` (PEP 621, cited). It makes **no new** assertions about
Cyclopts, pytest-timeout-under-xdist, or uv behaviour — it explicitly leaves all
of those untouched. This satisfies the standing rule.

## Findings by lens

### Pandalump (structural integrity) — sound

Dependency direction is correct and acyclic: `names.py` holds only strings and
imports nothing from `stub.py`; `stub.py` imports `names.py`; tests import both.
No circular import. The registry as source-of-truth with `[project.scripts]`
asserted against it (rather than inverted) is the right call — the build backend
must read the TOML, and parsing TOML inside the package at import time would add
I/O to every command's import path. 🟢

### Telefono (contracts) — sound, one advisory

The externally observable contract (five scripts on PATH, exit 2, message,
`STUB_EXIT_CODE`, e2e assertions) is explicitly preserved. The order test
compares `list(parsed)` to `list(COMMAND_NAMES)`, catching reordering as well as
missing/extra names. 🟢

🟡 Advisory: after Work item 3, `tests/test_pyproject_scripts.py` (now deriving
`EXPECTED_SCRIPTS` from `names.project_scripts_table()`) and the new
`test_command_names_registry.py::test_registry_matches_project_scripts` assert
nearly the same thing. The plan flags this and defers the keep/fold decision to
the implementer. Recommend the plan **commit** to keeping both with a one-line
note on their distinct roles (fast equality vs order+callable+five-name pin), so
the implementer does not have to adjudicate redundancy mid-build.

### Buzzy Bee (scaling) — not applicable, correctly

Five-entry fixed mapping; no scaling surface. The plan's rejection of
snapshot/property suites is correct and justified against AGENTS.md snapshot
discipline and `python-verification`. 🟢

### Doggylump (failure modes) — sound

The gate fails `make test` on any drift (added sixth command, rename,
reordering, broken `module:func` binding). Pre-mortem: the most plausible
6-month failure is a contributor adding a command to `[project.scripts]` but not
the registry — caught by `test_registry_matches_project_scripts`. The second is
a contributor editing the registry but not `pyproject.toml` — same gate catches
it. Both blast radii are a red CI, not a shipped defect. 🟢

### Wafflecat (alternatives) — the proposed design wins

Strongest alternative: derive names by reading `[project.scripts]` at runtime
inside the package (TOML as sole source). The plan correctly rejects this — it
inverts the dependency, adds an import-time file read and file-location
dependency to every command, and is listed as an escalation trigger. A second
alternative — generating the five `stub.py` functions via `setattr` in a loop —
is correctly rejected because it hides symbols from `module:func` resolution and
static analysis. No credible alternative beats the proposal; that is a strong
signal.

### Dinolump (long-term viability) — sound

Matches the team's existing tooling (tomllib already used, no new dep, frozen
`MappingProxyType` is idiomatic). The developers'-guide cross-reference gives
future contributors the single edit point. 🟢

## Advisory items (non-blocking; the implementer must heed Constraints)

1. 🟡 **Illustrative snippets would not pass lint as written.** Ruff selects `D`
   (pydocstyle) and `ANN` with `preview = true`, and `interrogate --fail-under
   100` runs over `tests` too. The illustrative `names.py` (lines 411–441,
   728–756) omits the **module docstring** (`D100`), and the illustrative gate
   (lines 770–791) shows `_parse_scripts` and the four `test_*` functions
   **without docstrings** (`D103`). `test_*.py` per-file-ignores cover `S101`,
   `PLR2004`, `PLR6301`, `PLR0913`, `PLR0917` — but **not** `D`. The plan's
   Constraints section already mandates full docstrings, so this is a trap only
   if the implementer copies the snippets verbatim. Recommend a one-line caveat
   on each snippet: "illustrative; add module and per-function docstrings before
   committing (Ruff `D`, interrogate 100%)."

2. 🟡 **Work item 2's `_name_for` reverse lookup is under-pinned.** The plan
   offers two shapes (a value→key reverse lookup helper, or a per-function name
   constant) and leaves the choice open. The reverse lookup adds a function that
   needs its own docstring and is slightly fragile (assumes function names are
   unique values, which they are). Prefer the plan **name** the simpler option
   as default — bind each function's console-script name from the registry
   directly, e.g. a module-level `NAMES = {v: k for k, v in
   COMMAND_ENTRY_POINTS.items()}` reverse map computed once — rather than a
   per-call lookup, and pin it so the implementer does not improvise.

3. 🟢 **Intermediate triple-duplication is expected but unstated.** At the end of
   Work item 1, the name lives in `names.py`, `stub.py` (still inline), and
   `pyproject.toml` simultaneously; the "two data sources is a defect" constraint
   is an *end-state* invariant, resolved by Work items 2–3. The plan's ordering
   is correct and each commit is green; a one-line note that the constraint binds
   the final state, not intermediate commits, would pre-empt a reviewer
   objection.

## Atomicity / ordering / testability / completeness

- **Atomic & independently committable:** yes. WI1 (registry + gate) passes
  standalone against unchanged `[project.scripts]`. WI2 (stub + stub tests) keeps
  the gate green because the functions still resolve. WI3 (import swaps + doc).
- **Ordered:** correct — source-of-truth first, consumers after.
- **Testable:** the new gate is the load-bearing validation; every claim has an
  observable check; `make all`/`markdownlint`/`nixie` named per item.
- **Complete:** all five duplication sites named in the roadmap remediation are
  addressed (stub.py, pyproject.toml, three test modules) plus the doc.

## Boundary / contract conformance

No contradiction with the deterministic/judgemental boundary (ADR-001), the
shared interface contract (ADR-003, correctly deferred), the five-script surface
(ADR-005), or the console-script distribution form (ADR-004). en-GB Oxford
spelling, 400-line limit, tests-under-`tests/`, and snapshot discipline are all
respected.

## Conclusion

The plan is implementable and design-conformant as written. The three advisory
items would strengthen it but none blocks implementation: the Constraints
section already binds the implementer to the docstring/lint requirements and the
registry shape, and the open decisions (test redundancy, `_name_for` shape) have
correct escalation triggers. **Proceed with conditions** — fold in the advisories
at the planner's discretion.
