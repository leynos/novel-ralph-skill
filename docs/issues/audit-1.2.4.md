# Post-merge audit — roadmap task 1.2.4

Audit of the codebase after roadmap task 1.2.4 ("Introduce a single source of
truth for the five command names") merged to `main` at commit `c4b9cf2`. Primary
scope is the code and documentation introduced or touched by that task: the new
registry module [`novel_ralph_skill/commands/names.py`](../../novel_ralph_skill/commands/names.py),
the rewired stubs in [`novel_ralph_skill/commands/stub.py`](../../novel_ralph_skill/commands/stub.py),
the new gate [`tests/test_command_names_registry.py`](../../tests/test_command_names_registry.py),
the converged [`tests/test_command_stubs.py`](../../tests/test_command_stubs.py),
[`tests/test_console_scripts_e2e.py`](../../tests/test_console_scripts_e2e.py),
and [`tests/test_pyproject_scripts.py`](../../tests/test_pyproject_scripts.py),
and the developer-guide note. The audit also re-checks whether the open items in
`docs/issues/audit-1.2.1.md`, `docs/issues/audit-1.2.2.md`, and
`docs/issues/audit-1.2.3.md` have been actioned.

The merged slice does what the roadmap asked: the five names now live once, as an
ordered data registry, and the entry-point stubs and all four test surfaces derive
their names from it. The previously-recorded duplication of the *names* themselves
(audit-1.2.1 Finding 1, audit-1.2.2 Finding 4, audit-1.2.3 Finding 4) is resolved.
Each finding below records a category, a location, a description, a concrete
proposed fix, and a severity. None is a blocking defect; they are tidy-up
opportunities plus prior-audit items that remain open.

## Finding 1 — `test_pyproject_scripts.py` and `test_command_names_registry.py` assert the same registry-equals-scripts invariant

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`tests/test_pyproject_scripts.py:20`](../../tests/test_pyproject_scripts.py)
  (`test_project_scripts_table_lists_the_five_commands`),
  [`tests/test_command_names_registry.py:27`](../../tests/test_command_names_registry.py)
  (`test_registry_matches_project_scripts`)

This slice converged `test_pyproject_scripts.py` onto the registry by replacing
its hand-written `EXPECTED_SCRIPTS` with `names.project_scripts_table()`. The side
effect is that its sole test now asserts `scripts == names.project_scripts_table()`
— byte-for-byte the same assertion the new
`test_command_names_registry.py::test_registry_matches_project_scripts` makes. Both
parse `pyproject.toml [project.scripts]` from `_PROJECT_ROOT` and compare it to
the registry-derived table. The two modules also each redeclare `_PROJECT_ROOT`
and
each carry their own near-identical `tomllib.loads((... / "pyproject.toml")
.read_text(encoding="utf-8"))` parse (see Finding 2). The registry module is now
the single source of truth, so the registry test (which also covers order,
callable resolution, and the exact five names) is the natural home for this gate;
`test_pyproject_scripts.py` is left asserting a strict subset of it.

**Proposed fix:** retire the redundant assertion. Either delete
`tests/test_pyproject_scripts.py` and let `test_command_names_registry.py` own the
registry-vs-`[project.scripts]` contract in full, or, if a fast standalone
"does the table parse and list five names" smoke check is still wanted, reduce
`test_pyproject_scripts.py` to an assertion the registry test does *not* make (for
example `len(scripts) == 5` without re-comparing the whole table). The aim is one
authoritative equality check, not two copies that must be kept in step.

## Finding 2 — `pyproject.toml` parsing is hand-rolled in two test modules

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`tests/test_command_names_registry.py:21`](../../tests/test_command_names_registry.py)
  (`_parse_scripts`),
  [`tests/test_pyproject_scripts.py:22`](../../tests/test_pyproject_scripts.py)
  (inline `tomllib.loads(...)`)

Two test modules read and parse the same `pyproject.toml` to reach
`["project"]["scripts"]`. `test_command_names_registry.py` extracts a private
`_parse_scripts()` helper; `test_pyproject_scripts.py` inlines the identical
`tomllib.loads((_PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))`
expression. Both also independently compute `_PROJECT_ROOT =
Path(__file__).resolve().parent.parent`, which `test_console_scripts_e2e.py`
computes a third time — exactly the shared-fixture gap audit-1.2.1 Finding 3
recorded, still unactioned because no `tests/conftest.py` exists.

**Proposed fix:** introduce `tests/conftest.py` (the home audit-1.2.1 Finding 3
already proposes) hosting a `project_root` fixture (or module constant) and a
`project_scripts()` helper that parses `[project.scripts]` once. Have both
pyproject-reading tests consume it. This removes the third `_PROJECT_ROOT` copy
and the duplicated parse in one move, and gives the catalogue/resolver helpers
proposed by audit-1.2.3 Findings 1 and 2 a place to live.

## Finding 3 — The registry-to-stub binding is exercised only structurally, never that each script name reaches its own body

- **Category:** test-gap
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/commands/stub.py:21`](../../novel_ralph_skill/commands/stub.py)
  (`_NAME_FOR` reverse map and the five entry points),
  [`tests/test_command_names_registry.py:42`](../../tests/test_command_names_registry.py)
  (`test_entry_points_resolve_to_callables`)

Task 1.2.4 added a reverse map `_NAME_FOR = {func: name for name, func in
COMMAND_ENTRY_POINTS.items()}` so each entry point reads its console-script name
from the registry (`make_stub_app(_NAME_FOR["novel_state"])`). The registry test
only asserts each function *resolves to a callable*; the stub test
(`test_entry_point_callable_exits_two`) drives each entry point and asserts the
name appears in stderr, which does cover the binding. The narrow gap is that no
test pins the *pairing* — that `novel_state` emits `novel-state` and not, say,
`novel-done`. Because `test_entry_point_callable_exits_two` is parametrized over
`(name, entry_point)` pairs drawn from the *same* `COMMAND_ENTRY_POINTS` mapping
the production code uses, a transposed key in `_NAME_FOR` (e.g. a future hand edit
mapping `novel_state` to the wrong name) would be masked: both the expectation and
the code would shift together. The reverse-map construction itself is not directly
unit-tested.

**Proposed fix:** add a focused assertion that the reverse map round-trips the
registry — for example `assert stub._NAME_FOR == {func: name for name, func in
COMMAND_ENTRY_POINTS.items()}` is circular, so instead pin one concrete pair
against a literal (e.g. `assert stub._NAME_FOR["novel_state"] == "novel-state"`)
or assert `set(stub._NAME_FOR.values()) == set(COMMAND_NAMES)` and that the map
injective (`len(stub._NAME_FOR) == len(COMMAND_NAMES)`). This catches a
collision or transposition in the reverse map that the same-source parametrization
cannot see.

## Finding 4 — `STUB_MODULE` is the registry's single source for the module path, but `pyproject.toml` still spells it five times

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/commands/names.py:18`](../../novel_ralph_skill/commands/names.py)
  (`STUB_MODULE`),
  [`pyproject.toml` `[project.scripts]`](../../pyproject.toml) (five
  `novel_ralph_skill.commands.stub:...` targets)

The registry centralises the module path as `STUB_MODULE =
"novel_ralph_skill.commands.stub"` and `project_scripts_table()` builds every
target as `f"{STUB_MODULE}:{func}"`. `pyproject.toml` necessarily repeats the same
module string five times because the build backend reads it verbatim — this is
inherent and correct, and `test_registry_matches_project_scripts` guards the two
against drift. The residual observation is that the *guard* is the only thing
keeping `STUB_MODULE` and the five TOML targets aligned; if the stub module were
ever relocated, a contributor must update both `STUB_MODULE` and five TOML lines,
and only the test failure would remind them. This is low severity because the gate
exists and fires, but the asymmetry (one constant vs five literals) is a small
ergonomic trap.

**Proposed fix:** no code change is strictly required — the test enforces the
invariant. If a contributor-facing reminder is wanted, add a one-line comment
above `[project.scripts]` in `pyproject.toml` noting that the table is asserted
against `novel_ralph_skill.commands.names` and must be regenerated from
`project_scripts_table()` if the module moves, so the human editing TOML learns
the
single-source-of-truth relationship without running the suite. Record the decision
to keep the duplication (build-backend constraint) so it is not re-flagged.

## Finding 5 — `interrogate` remains installed but unconfigured and ungated

- **Category:** test-gap
- **Severity:** low
- **Location:** [`pyproject.toml`](../../pyproject.toml) (`interrogate` under
  `[dependency-groups].dev`; no `[tool.interrogate]` block, no Makefile target,
  no
  CI step)

`interrogate` is still a dev dependency with no `[tool.interrogate]`
configuration, no Makefile target, and no CI invocation, so docstring coverage is
unenforced — as audit-1.2.1 Finding 4, audit-1.2.2 Finding 4, and audit-1.2.3
Finding 5 all recorded. The new `names.py` and the converged tests are in fact
fully docstringed, which is precisely why locking the gate in now is cheap.
Roadmap task 1.2.5 ("docstring-coverage gate (interrogate)") owns this and is
unactioned at this commit.

**Proposed fix:** action roadmap task 1.2.5: add a `[tool.interrogate]` block with
an explicit `fail-under` threshold and wire an `interrogate` invocation into the
lint gate (a Makefile target plus a CI step), or remove `interrogate` from the dev
group if the gate is intentionally deferred. No new work is required of this audit
beyond confirming the item is still open and lives in the roadmap.

## Notes on what was checked and found sound

- **The roadmap objective is met.** The five names live once, as the ordered
  `COMMAND_ENTRY_POINTS` mapping wrapped in a `MappingProxyType` so callers cannot
  mutate the registry, with `COMMAND_NAMES` and `project_scripts_table()` derived
  from it. The stubs, all four test modules, and the `[project.scripts]` gate now
  read from this one source. The name duplication carried since audit-1.2.1 is
  resolved.
- **Immutability and CQS.** `COMMAND_ENTRY_POINTS` is a read-only proxy;
  `project_scripts_table()` returns a fresh `dict` per call (documented) so callers
  cannot reach back through it to the registry. Both `project_scripts_table()` and
  `_parse_scripts()` are pure queries; `make_stub_app` is a query that returns an
  app whose *invocation* carries the side effect, which the docstring calls out.
  No command/query separation concern.
- **Ordering is tested, not just equality.** `test_registry_order_matches_table`
  guards against a reordering that the order-insensitive dict equality would miss,
  exploiting `tomllib`'s key-order preservation — a thoughtful, non-obvious check.
- **Documentation.** The registry module carries a clear module docstring naming
  ADR 004 and ADR 005, every public symbol is documented, and the developer guide
  was updated to point contributors at `names.py` ("Edit a command name there, not
  in five places"). The `why:` comments on `_NAME_FOR` and the stub body record
  load-bearing reasons inline.
- **Prose conventions.** The slice's prose follows en-GB Oxford spelling and the
  `AGENTS.md` quality gates (`make all`) pass on the merged change.
