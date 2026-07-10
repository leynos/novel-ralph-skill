# Post-merge audit — roadmap task 1.2.5

Audit of the codebase after roadmap task 1.2.5 ("Establish a
docstring-coverage gate (interrogate) for the Python package") merged to `main`
at commit `1b4bfd8`. Primary scope is the code and documentation introduced or
touched by that task: the new `[tool.interrogate]` table in
[`pyproject.toml`](../../pyproject.toml), the migrated `lint-python` recipe in
[`Makefile`](../../Makefile), the new guard
[`tests/test_interrogate_gate.py`](../../tests/test_interrogate_gate.py), and the
reconciled prose in [`AGENTS.md`](../../AGENTS.md),
[`docs/developers-guide.md`](../../docs/developers-guide.md), and
[`docs/users-guide.md`](../../docs/users-guide.md). The audit also re-checks
whether the open items carried in `docs/issues/audit-1.2.1.md` through
`docs/issues/audit-1.2.4.md` have been actioned.

The merged slice does what the roadmap asked: the 100% docstring threshold now
lives once in `[tool.interrogate] fail-under = 100`, the `lint-python` recipe
sources it from there (the `--fail-under 100` literal is gone), a guard test
pins the config value, the same-line Makefile invocation, and the dev
dependency, and all four prose homes were reconciled. The
interrogate-unconfigured-and-ungated item carried since audit-1.2.1 Finding 4 is
resolved. Each finding below records a category, a location, a description, a
concrete proposed fix, and a severity. None is a blocking defect; they are
tidy-up opportunities plus prior-audit items that remain open and have grown by
one copy with this slice.

## Finding 1 — `_PROJECT_ROOT` is now redeclared in four test modules, and the new guard adds the fourth

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`tests/test_interrogate_gate.py:21`](../../tests/test_interrogate_gate.py),
  [`tests/test_command_names_registry.py:18`](../../tests/test_command_names_registry.py),
  [`tests/test_pyproject_scripts.py:17`](../../tests/test_pyproject_scripts.py),
  [`tests/test_console_scripts_e2e.py:39`](../../tests/test_console_scripts_e2e.py)

`_PROJECT_ROOT = Path(__file__).resolve().parent.parent` is now spelt
identically in four test modules. This slice's new
`tests/test_interrogate_gate.py` added the fourth copy rather than consuming a
shared home. This is the exact shared-fixture gap audit-1.2.1 Finding 3 raised
and audit-1.2.4 Finding 2 carried forward: there is still no
`tests/conftest.py`, so every new test module that needs the project root
re-derives it. The drift risk is low (the expression is fixed), but the count is
now growing one-per-slice, which is the signal that the shared home is overdue.

**Proposed fix:** introduce `tests/conftest.py` (the home proposed since
audit-1.2.1 Finding 3) exposing a `project_root` fixture or module constant, and
have all four modules consume it. This is the same conftest that audit-1.2.3
Findings 1-2 and audit-1.2.4 Finding 2 want for the cuprum-catalogue helper, the
`_venv_scripts_dir` resolver, and the shared pyproject parse; landing it now,
while the surface is small, removes four copies in one move and gives the other
deferred helpers a place to live.

## Finding 2 — Three test modules now hand-roll the same `pyproject.toml` parse

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`tests/test_interrogate_gate.py:27`](../../tests/test_interrogate_gate.py)
  (`_pyproject`),
  [`tests/test_command_names_registry.py:21`](../../tests/test_command_names_registry.py)
  (`_parse_scripts`),
  [`tests/test_pyproject_scripts.py:22`](../../tests/test_pyproject_scripts.py)
  (inline `tomllib.loads(...)`)

Three modules now read and parse the same `pyproject.toml` with the identical
`tomllib.loads((_PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))`
expression. audit-1.2.4 Finding 2 recorded two such copies; this slice's
`_pyproject()` helper makes three. The shapes differ only in which sub-table each
test reaches (`[project.scripts]`, `[tool.interrogate]`,
`[dependency-groups]`), so the raw-parse step is pure boilerplate that wants to
be shared.

**Proposed fix:** host a single `pyproject()` helper (cached) in the
`tests/conftest.py` proposed in Finding 1, returning the parsed document once,
and have the three modules select their sub-table from it. This removes the
duplicated read-and-parse and pairs naturally with the `_PROJECT_ROOT`
consolidation, so both land together.

## Finding 3 — The `_table` table-narrowing helper is general but lives privately in one guard module

- **Category:** separation-of-concerns
- **Severity:** low
- **Location:**
  [`tests/test_interrogate_gate.py:32`](../../tests/test_interrogate_gate.py)
  (`_table`)

`_table(parent, key)` is a reusable, behaviour-bearing utility: it fetches a
sub-table from a parsed TOML mapping and asserts via `match`/`case` that the
value is a `dict`, raising an `AssertionError` with a precise message otherwise.
Every pyproject-reading guard needs exactly this narrowing step before it can
index a `[tool.*]` or `[project.*]` table — `test_command_names_registry.py` and
`test_pyproject_scripts.py` currently index `["project"]["scripts"]` without the
type guard, so a malformed TOML would raise a less helpful `TypeError` there.
The helper is good; its private, single-module home means the other guards
cannot benefit from it and may re-implement a weaker version.

**Proposed fix:** when `tests/conftest.py` lands (Findings 1-2), move `_table`
there as a shared, non-underscored helper (for example `toml_table`) and have
the registry and scripts guards reach their sub-tables through it. This gives one
typed accessor for the whole test suite and removes the asymmetry where only the
newest guard validates table shape.

## Finding 4 — `test_registry_matches_project_scripts` and `test_project_scripts_table_lists_the_five_commands` still assert the same invariant

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`tests/test_pyproject_scripts.py:20`](../../tests/test_pyproject_scripts.py)
  (`test_project_scripts_table_lists_the_five_commands`),
  [`tests/test_command_names_registry.py:27`](../../tests/test_command_names_registry.py)
  (`test_registry_matches_project_scripts`)

audit-1.2.4 Finding 1 recorded that both tests assert
`scripts == names.project_scripts_table()` — byte-for-byte the same equality,
each parsing `[project.scripts]` from `_PROJECT_ROOT`. This slice did not touch
either, so the redundancy is unchanged: two modules own one contract, and the
registry test (which also covers order, callable resolution, and the exact five
names) is the natural sole owner. Re-recording so the duplication is not lost to
view.

**Proposed fix:** retire the redundant assertion as audit-1.2.4 Finding 1
proposed — either delete `tests/test_pyproject_scripts.py` and let the registry
test own the contract in full, or reduce it to a check the registry test does
not make (for example `len(scripts) == 5`) so there is one authoritative equality
rather than two copies kept in step. If both modules are kept, fold their parse
onto the shared `pyproject()` helper from Finding 2 so at least the parsing is
not also duplicated.

## Finding 5 — Cuprum catalogue boilerplate and the cross-module `_venv_scripts_dir` import remain unaddressed

- **Category:** separation-of-concerns
- **Severity:** medium
- **Location:**
  [`tests/test_console_scripts_e2e.py:50`](../../tests/test_console_scripts_e2e.py)
  (module `_CATALOGUE`),
  [`tests/test_console_scripts_e2e.py:122`](../../tests/test_console_scripts_e2e.py)
  (per-command catalogue),
  [`tests/test_venv_scripts_dir.py:37`](../../tests/test_venv_scripts_dir.py)
  (resolver-test catalogue),
  [`tests/test_venv_scripts_dir.py:18`](../../tests/test_venv_scripts_dir.py)
  (`from tests.test_console_scripts_e2e import _venv_scripts_dir`)

The single-program `ProgramCatalogue`/`ProjectSettings` construction is still
built three times (audit-1.2.3 Finding 1), and `test_venv_scripts_dir.py` still
reaches across a package boundary to import the private `_venv_scripts_dir` from
`test_console_scripts_e2e.py` (audit-1.2.3 Finding 2). This slice did not touch
the e2e surface, so both remain open. They are recorded here only to confirm they
are still live and to bundle them with the conftest work the four findings above
all converge on.

**Proposed fix:** in the same `tests/conftest.py` introduced for Findings 1-3,
add a `single_program_catalogue(program, name)` helper (audit-1.2.3 Finding 1)
and move `_venv_scripts_dir` to a shared, public home so neither test imports a
private symbol from the other (audit-1.2.3 Finding 2). One conftest closes the
duplication and separation-of-concerns items that have accrued across four
audits.

## Finding 6 — `docs/contents.md` omits ADR 006, the issues set, and the execplans set

- **Category:** docs-gap
- **Severity:** low
- **Location:** [`docs/contents.md:17`](../../docs/contents.md) (the ADR
  section stops at ADR 005), and the absence of any entry for `docs/issues/` or
  `docs/execplans/`

The documentation index lists ADRs 001-005 but not
`docs/adr-006-console-scripts-e2e-posix-policy.md`, which exists and is the
governing policy cited throughout the e2e tests (and by ADR-006's own
cross-reference). A reader using `contents.md` as the map misses the POSIX-only
policy entirely. The index also has no entry for the growing `docs/issues/`
audit set (now five files including this one) or the `docs/execplans/` set, so a
new contributor cannot discover the audit trail or the per-task execution plans
from the index.

**Proposed fix:** add ADR 006 to the "Architecture decision records" list in
`contents.md`, and add a short section (or two bullets) pointing at the
`docs/issues/` post-merge audit set and the `docs/execplans/` execution-plan set
so both are discoverable from the index. This is index maintenance, not a
restructuring; running `make markdownlint` and `make nixie` over the edit
suffices.

## Finding 7 — No guard pins `[tool.interrogate]`'s `ignore-*` flags, so the gate can be silently relaxed

- **Category:** test-gap
- **Severity:** low
- **Location:**
  [`pyproject.toml:305`](../../pyproject.toml) (`[tool.interrogate]`,
  the seven `ignore-* = false` flags),
  [`tests/test_interrogate_gate.py:52`](../../tests/test_interrogate_gate.py)
  (`test_fail_under_is_one_hundred`)

The new guard pins `fail-under == 100`, the same-line Makefile invocation, and
the dev dependency — the three regressions the execplan named. It does not assert
the `ignore-*` flags stay `false`. The execplan's own config-surface tolerance
treats adding `exclude`/`omit-covered-files` or flipping an `ignore-*` to `true`
as a gate-relaxing change, yet a contributor could set, say,
`ignore-nested-functions = true` or `ignore-module = true` and shrink what the
100% threshold measures without failing any test — the threshold would still read
100, but of fewer nodes. This is the same "what is measured" surface the guard
otherwise protects.

**Proposed fix:** extend `test_interrogate_gate.py` with one assertion that no
relaxing key is set — for example, assert the parsed `[tool.interrogate]` table
contains no `exclude`/`omit-covered-files` key and that every present `ignore-*`
flag is `false`. This closes the residual hole so the gate's *scope*, not only
its *threshold*, is pinned against silent relaxation. Keep it a single
data-driven assertion so it does not need to enumerate the flag names by hand if
the set grows.

## Notes on what was checked and found sound

- **The roadmap objective is met.** The 100% threshold lives once in
  `[tool.interrogate] fail-under = 100`; the `lint-python` recipe sources it
  (the `--fail-under 100` literal is gone); the guard pins the config value, the
  same-line invocation, and the dev dependency; and all four prose homes
  (AGENTS.md, the developers' guide twice, the users' guide) were reconciled. A
  bare `interrogate` invocation now inherits 100% from config rather than the
  silent 80% default. The interrogate-ungated item carried since audit-1.2.1
  Finding 4 is resolved.
- **Guard quality.** The Makefile assertion checks *same-line* co-occurrence of
  `interrogate` and `$(PYTHON_TARGETS)`, so deleting the recipe line fails the
  gate even though `$(PYTHON_TARGETS)` appears on other lines — a deliberate,
  non-tautological check. The dev-dependency assertion normalizes each PEP 508
  requirement to its bare distribution name via `_dist_name`, so it holds across
  version specifiers and extras. The `_table` helper narrows TOML values with
  `match`/`case` and a precise failure message.
- **Command/query separation.** `_pyproject`, `_table`, and `_dist_name` are
  pure queries; the guard's side effect is confined to pytest assertions. No CQS
  concern.
- **Documentation.** The config table carries a `why:`-style comment explaining
  that the threshold is the single source of truth and that the `ignore-*` flags
  are documentary, not exemptions. The guard module's docstring records why it
  parses statically rather than shelling out to `interrogate` (the live gate
  already runs in `make lint`). Every public symbol is documented; the package
  and tests stay at 100% coverage.
- **Prose conventions.** The slice's prose follows en-GB Oxford spelling and the
  `AGENTS.md` quality gates (`make all`, `make markdownlint`, `make nixie`) pass
  on the merged change.
