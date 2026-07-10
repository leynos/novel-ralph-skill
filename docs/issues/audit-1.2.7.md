# Post-merge audit — roadmap task 1.2.7

Audit of the codebase after roadmap task 1.2.7 ("Introduce shared conftest
scaffolding") merged to `main` at commit `2d7297e`. Primary scope is the
consolidation that task introduced —
[`tests/conftest.py`](../../tests/conftest.py) and the migration of
[`test_command_names_registry`](../../tests/test_command_names_registry.py),
[`test_console_scripts_e2e`](../../tests/test_console_scripts_e2e.py),
[`test_interrogate_gate`](../../tests/test_interrogate_gate.py),
[`test_pyproject_scripts`](../../tests/test_pyproject_scripts.py),
[`test_state_layout_reference`](../../tests/test_state_layout_reference.py), and
[`test_venv_scripts_dir`](../../tests/test_venv_scripts_dir.py) onto the shared
fixtures — plus the new
[`test_conftest_helpers`](../../tests/test_conftest_helpers.py) and the
developers' guide section recording the convention. The audit also re-checks
whether the open items carried in `docs/issues/audit-1.2.1.md` through
`docs/issues/audit-1.2.6.md` have been actioned by this slice.

The merged slice does what the roadmap asked, and it discharges the
longest-running finding in the audit trail: the duplicated `_PROJECT_ROOT`,
`pyproject` parse, repo-file reader, `_table` accessor, cuprum-catalogue
builder, and `_venv_scripts_dir` resolver — flagged across audits 1.2.1, 1.2.3,
1.2.4, 1.2.5, and 1.2.6 — now live once in `tests/conftest.py` and are consumed
by fixture name. The conftest is inside `$(PYTHON_TARGETS)`, so it carries full
docstrings, no bare `assert`, and a focused `test_conftest_helpers` suite. That
is the right shape.

The residual findings below are the helpers the migration did not reach. The
consolidation closed the six modules in its own scope but left a seventh test
module — `test_contract_test_deps.py`, landed in parallel by roadmap task 1.3.1
at commit `2270db9` — outside the new home, still hand-rolling the same
`pyproject` parse and dev-dependency-group extraction the conftest now owns. A
second copy of dependency-name normalization logic now exists, and the two
copies disagree on correctness. The `docs/contents.md` index gaps carried since
audit 1.2.5 also remain.

Each finding records a category, a location, a description, a concrete proposed
fix, and a severity. None is a blocking defect; they are tidy-up opportunities
plus prior-audit items still open.

## Finding 1 — `test_contract_test_deps.py` was not migrated onto the new conftest fixtures

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`tests/test_contract_test_deps.py:30`](../../tests/test_contract_test_deps.py)
  (`_PYPROJECT`),
  [`tests/test_contract_test_deps.py:33`](../../tests/test_contract_test_deps.py)
  (`_dev_dependencies`),
  [`tests/conftest.py:47`](../../tests/conftest.py) (the `pyproject` fixture),
  [`tests/conftest.py:87`](../../tests/conftest.py) (the `toml_table` fixture)

`tests/conftest.py` now owns the `pyproject` parse (`pyproject` fixture) and the
table-narrowing accessor (`toml_table` fixture), and task 1.2.7's stated goal
was to remove exactly the "resolve `pyproject.toml` off a per-module
`_PROJECT_ROOT` and parse it with `tomllib`" duplication. `test_contract_test_deps`
still does this itself:
`_PYPROJECT = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"`
followed by `tomllib.loads(_PYPROJECT.read_text(...))` inside
`_dev_dependencies`. It is the seventh test module reading `pyproject.toml`, and
the one the migration did not reach because it landed on a parallel branch
(1.3.1) at the same time. The drift risk per copy is low, but this is the same
shared-fixture gap the conftest was built to close, reappearing one module after
the close.

**Proposed fix:** migrate `test_contract_test_deps` onto the shared fixtures:
have the dev-dependency tests take `pyproject` and `toml_table` as parameters
and read the dev group as
`toml_table(pyproject, "dependency-groups")["dev"]`, deleting `_PYPROJECT` and
`_dev_dependencies`. The two version-pin tests
(`test_hypothesis_import_and_version`, `test_syrupy_version`) read installed
distribution metadata rather than `pyproject.toml`, so they stay as they are.

## Finding 2 — Dependency-name normalization is duplicated and the two copies disagree

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`tests/test_interrogate_gate.py:24`](../../tests/test_interrogate_gate.py)
  (`_DIST_NAME` regex and `_dist_name`),
  [`tests/test_contract_test_deps.py:79`](../../tests/test_contract_test_deps.py)
  (the inline `spec.split()[0].split(">")[0].split("=")[0]` expression)

Two test modules independently normalize a PEP 508 requirement string to its
bare distribution name in order to assert a dependency is declared in
`[dependency-groups].dev`. `test_interrogate_gate` uses a documented regex
(`_DIST_NAME`) that correctly stops at the first non-name character, so it
handles version specifiers, an extras bracket (`interrogate[toml]`), and
environment markers. `test_contract_test_deps` uses an inline
`spec.split()[0].split(">")[0].split("=")[0]`, which is both a second copy of
the same intent and strictly weaker: it splits only on whitespace, `>`, and `=`,
so an extras form such as `hypothesis[cli]` or a `~=`/`<` specifier would leak
the bracket or operator into the "name", and the assertion could spuriously fail
on a legitimate future edit. The same logic existing twice, with one copy
buggier than the other, is the classic divergence trap.

**Proposed fix:** lift the requirement-name normalizer into `tests/conftest.py`
as a fixture (for example `dist_name` returning a `(spec: str) -> str | None`
callable backed by the `_DIST_NAME` regex), and have both
`test_interrogate_gate` and `test_contract_test_deps` consume it. This removes
the second copy and replaces the weaker `split`-chain with the regex that
already handles extras and markers. Pair it with Finding 1 so the contract-deps
module reaches the shared home in one move.

## Finding 3 — `test_command_names_registry` keeps a private `_parse_scripts` rather than a shared scripts accessor

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`tests/test_command_names_registry.py:21`](../../tests/test_command_names_registry.py)
  (`_parse_scripts`),
  [`tests/test_pyproject_scripts.py:24`](../../tests/test_pyproject_scripts.py)
  (the inline `toml_table(toml_table(pyproject, "project"), "scripts")`)

Both `test_command_names_registry` and `test_pyproject_scripts` narrow the
`pyproject` mapping down to the `[project.scripts]` table. The former wraps the
two-level `toml_table` access in a module-private `_parse_scripts(pyproject,
toml_table)` helper; the latter inlines the identical
`toml_table(toml_table(pyproject, "project"), "scripts")`. The expression is the
same nested-table access in both, so the same "reach `[project.scripts]`" intent
is spelt two ways across the two modules the conftest migration touched. This is
minor — both already consume the shared fixtures, so only the leaf accessor
differs — but it is a residual seam the migration could have folded.

**Proposed fix:** expose a small `project_scripts(pyproject)` fixture in
`tests/conftest.py` (or a more general `toml_path(pyproject, *keys)` walker that
chains `toml_table` over a key sequence) and have both modules consume it,
deleting `_parse_scripts`. Defer if preferred: the duplication is two call sites
of a one-line expression, so the cost of leaving it is low, but recording it
keeps the conftest the single home for table navigation rather than letting
per-module accessors regrow.

## Finding 4 — The slice introduced a markdownlint MD012 violation that breaks `make markdownlint` on `main`

- **Category:** inconsistency
- **Severity:** medium
- **Location:**
  [`docs/developers-guide.md:19`](../../docs/developers-guide.md) (two
  consecutive blank lines immediately above the new "Shared test scaffolding"
  heading at line 21)

The 1.2.7 slice added the "Shared test scaffolding" section to the developers'
guide but left two consecutive blank lines between the preceding `make audit`
paragraph (ending line 18) and the new `## Shared test scaffolding` heading.
`make markdownlint` flags this as
`docs/developers-guide.md:20 MD012/no-multiple-blanks` and exits non-zero, so the
documentation lint gate currently fails on `main` — and would fail the same gate
in CI for any subsequent documentation pull request until the blank line is
removed. The "Notes on what was checked" section of this audit had to be
qualified accordingly: the slice's own claim that `make markdownlint` passes does
not hold for the merged tree.

**Proposed fix:** delete one of the two blank lines at
`docs/developers-guide.md:19-20` so a single blank line separates the `make
audit` paragraph from the `## Shared test scaffolding` heading, then re-run `make
markdownlint` to confirm a clean pass. This is a one-line edit; record it on the
next documentation-touching slice (or as a standalone docs fix) so the lint gate
is green before the next merge.

## Finding 5 — `docs/contents.md` still omits ADR 006, the issues set, and the execplans set, and now lags two further audits

- **Category:** docs-gap
- **Severity:** low
- **Location:** [`docs/contents.md:28`](../../docs/contents.md) (the ADR
  section stops at ADR 005), and the absence of any entry for `docs/issues/` or
  `docs/execplans/`

audit-1.2.5 Finding 6 and audit-1.2.6 Finding 3 recorded that the documentation
index lists ADRs 001-005 but not
`docs/adr-006-console-scripts-e2e-posix-policy.md`, and has no entry for the
growing `docs/issues/` audit set or the `docs/execplans/` execution-plan set.
This slice did not touch `contents.md`, so all three gaps remain. Since
audit-1.2.6 the issues set has grown to seven files (this audit included) and
the execplans set to eighteen, so the index's blind spot has widened by two
audits and several plans. A reader using `contents.md` as the map still misses
the POSIX-only console-scripts policy and cannot discover the audit trail or the
per-task execution plans from the index. ADR 003 is referenced throughout the
developers' guide for the now-landed envelope contract, which makes the missing
ADR 006 entry more conspicuous, not less.

**Proposed fix:** add ADR 006 to the "Architecture decision records" list in
`contents.md`, and add a short section (or two bullets) pointing at the
`docs/issues/` post-merge audit set and the `docs/execplans/` execution-plan set
so both are discoverable. This is index maintenance, not a restructuring; running
`make markdownlint` and `make nixie` over the edit suffices. The change is small
enough to fold into whichever slice next touches the documentation index.

## Finding 6 — The conftest docstring's audit cross-reference omits the audit that this slice closes

- **Category:** docs-gap
- **Severity:** low
- **Location:**
  [`tests/conftest.py:6`](../../tests/conftest.py) (the module docstring's
  "six post-merge audits flagged" parenthetical),
  [`docs/developers-guide.md:42`](../../docs/developers-guide.md) (the matching
  "This consolidation discharges ... findings" list)

Both the conftest module docstring and the developers' guide enumerate the
audits whose duplication findings the consolidation discharges, but each list
stops at audit-1.2.5 (the docstring) or audit-1.2.6 (the guide) without a forward
pointer to where the discharge is itself recorded. The docstring says "six
post-merge audits flagged" and then lists five citations (1.2.1, 1.2.3, 1.2.4,
1.2.5, 1.2.6); the count and the citation list disagree by one, which will read
as an off-by-one to a future maintainer auditing the claim. This is cosmetic —
no behaviour depends on it — but the mismatch between "six" and five cited files
is the kind of small inaccuracy these guards otherwise pride themselves on
pinning.

**Proposed fix:** reconcile the count with the citation list in the
`tests/conftest.py` docstring — either cite all six audits (add the sixth file)
or change "six post-merge audits flagged" to match the five distinct files
listed. No code change is needed; this is a one-line docstring correction that
the interrogate gate already covers, so `make lint` re-validates it.

## Notes on what was checked and found sound

- **The roadmap objective is met.** `tests/conftest.py` now owns `project_root`,
  `pyproject`, `read_repo_text`, `toml_table`, `single_program_catalogue`, and
  `venv_scripts_dir` as fixtures, and the six in-scope modules consume them by
  parameter name with no cross-module private import. The long-running
  duplication finding from audits 1.2.1 through 1.2.6 is discharged for those
  modules. The conftest carries a module docstring, a docstring on every fixture,
  and raises `AssertionError` directly rather than using bare `assert`, so it
  holds inside `$(PYTHON_TARGETS)` without `per-file-ignores` relief.
- **The new test coverage is honest and focused.**
  `test_conftest_helpers.py` exercises each fixture the way production modules
  do — `toml_table`'s happy and unhappy paths, `read_repo_text`,
  `project_root`, the parsed `pyproject` shape, and `single_program_catalogue`
  building a usable cuprum allowlist (including the absolute-path case that
  pins cuprum 0.1.0's no-path-validation behaviour) — without paying the slow
  wheel-build-and-install e2e cost.
- **No command/query concern.** Every conftest fixture is a pure query or
  returns a pure builder; the only side effects in the migrated modules are
  pytest assertions and the e2e's deliberate `uv` build/venv/install. The
  deterministic-versus-judgemental boundary (ADR-001) is untouched; this slice
  introduced no production code.
- **The developers' guide section is accurate.** The new "Shared test
  scaffolding" section names each fixture, states the consume-by-fixture-name
  convention, and records why importing from `conftest` or another test module
  is forbidden. It matches the conftest as merged.
- **Prose conventions.** The slice's prose follows en-GB Oxford spelling, and
  `make nixie` passes on the merged change. `make markdownlint` does **not** pass
  on the merged tree — see Finding 4 — because the developers' guide edit left a
  double blank line; that gate is green again once Finding 4 is actioned.
