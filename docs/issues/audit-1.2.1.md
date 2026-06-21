# Post-merge audit — roadmap task 1.2.1

Audit of the codebase after roadmap task 1.2.1 (wire the five console-script
entry points) merged to `main` at commit `5af36d1`. Scope is the code and
documentation introduced or touched by that task: the stub command surface
(`novel_ralph_skill/commands/stub.py`), the `[project.scripts]` table, the
three new test modules, and the developer/user guide updates.

Each finding records a location, a description, a concrete proposed fix, and a
severity. None of these are blocking defects; the merged slice is correct and
well tested. They are tidy-up opportunities to action before the command
bodies land in later slices, while the surface is still small.

## Finding 1 — The five command names are duplicated across five files

- **Category:** duplication
- **Severity:** medium
- **Location:** `novel_ralph_skill/commands/stub.py` (five `def` entry
  points), `pyproject.toml` `[project.scripts]`,
  `tests/test_command_stubs.py:23` (`COMMAND_NAMES`),
  `tests/test_console_scripts_e2e.py:47` (`COMMAND_NAMES`),
  `tests/test_pyproject_scripts.py:17` (`EXPECTED_SCRIPTS` keys)

The canonical list of the five command names — `novel-state`, `novel-done`,
`novel-compile`, `desloppify`, `wordcount` — is hand-written in five places.
`test_command_stubs.py` and `test_console_scripts_e2e.py` each declare an
identical `COMMAND_NAMES` tuple; `test_pyproject_scripts.py` re-states the same
names as `EXPECTED_SCRIPTS` keys; `stub.py` repeats them as function names and
string literals; `pyproject.toml` repeats them as table keys. ADR-005 fixes
these names, so any future rename touches five files and risks silent drift —
exactly the failure `test_pyproject_scripts.py` exists to catch, but only for
the pyproject-versus-stub axis.

**Proposed fix:** introduce a single registry in `stub.py`, for example a
module-level mapping `STUB_COMMANDS: dict[str, Callable[[], None]]` (name ->
entry point) or a tuple of `(name, callable)` pairs, and derive the five
`def` entry points and any test fixtures from it. Both test modules can then
import the names from the package instead of re-declaring them, and
`test_pyproject_scripts.py` can assert the `[project.scripts]` table against
the registry rather than a separately maintained literal. This makes the
package the single source of truth and reduces the rename blast radius to one
edit plus `pyproject.toml`.

## Finding 2 — Five near-identical entry-point functions

- **Category:** similarity
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/stub.py`, functions
  `novel_state`, `novel_done`, `novel_compile`, `desloppify`, `wordcount`

The five entry points differ only in the name string passed to
`make_stub_app`. Each is a two-line body of the shape
`make_stub_app("<name>")()`. The `make_stub_app` factory already removes the
duplication inside each app; the remaining repetition is the five thin
wrappers themselves. This is acceptable today because `[project.scripts]`
requires a named, importable callable per command, but it is worth recording
so the pattern is deliberate rather than accidental once real bodies arrive.

**Proposed fix:** keep one wrapper per command (the packaging contract needs
named callables), but generate or document them from the registry proposed in
Finding 1 so the relationship is explicit. If a factory-of-callables approach
is taken, assign the generated callables to module globals with `__name__`
set, and add a comment explaining why distinct top-level symbols are required
(entry-point resolution). Do not collapse them into a single dispatch
function: that would reintroduce a multiplexer, which ADR-005 explicitly
rejected.

## Finding 3 — `_PROJECT_ROOT` boilerplate duplicated in two test modules

- **Category:** duplication
- **Severity:** low
- **Location:** `tests/test_pyproject_scripts.py:14`,
  `tests/test_console_scripts_e2e.py:33`

Both modules compute
`_PROJECT_ROOT = Path(__file__).resolve().parent.parent` independently. This
is a small, well-understood idiom, but as the test suite grows the project
root is the kind of value that benefits from a single definition.

**Proposed fix:** expose the project root once as a session-scoped fixture in
a `tests/conftest.py` (none exists yet) and consume it from both modules.
This also gives a natural home for the shared command-name fixtures from
Finding 1.

## Finding 4 — No docstring-coverage gate despite `interrogate` being a dep

- **Category:** test-gap
- **Severity:** low
- **Location:** `pyproject.toml` (`interrogate` listed under
  `[dependency-groups].dev`; no `[tool.interrogate]` block)

`interrogate` is installed as a dev dependency, but there is no
`[tool.interrogate]` configuration and no Makefile target invoking it, so
docstring coverage is not enforced. The current modules are well documented,
which makes now the cheapest moment to lock that standard in before the
command bodies expand the surface.

**Proposed fix:** add a `[tool.interrogate]` block with an explicit
`fail-under` threshold and wire an `interrogate` invocation into the lint or
test gate (a Makefile target plus CI step), or remove `interrogate` from the
dev group if docstring coverage is intentionally not gated. Either resolves
the ambiguity of a tool that is installed but unused.

## Finding 5 — Stub message string is asserted in three places, defined once

- **Category:** inconsistency
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/stub.py` (the literal
  `f"{name} is not yet implemented"`), asserted via substring checks in
  `tests/test_command_stubs.py` and `tests/test_console_scripts_e2e.py`

The "not yet implemented" message format lives as an inline f-string in the
`_not_implemented` callback. Tests assert only that the command `name` appears
in stderr, not the full phrase, so the message wording can drift without any
test failing. The user guide quotes the exact phrase
(`docs/users-guide.md:88`), creating a documented contract the tests do not
pin.

**Proposed fix:** lift the message to a module-level template constant (for
example `NOT_IMPLEMENTED_TEMPLATE = "{name} is not yet implemented"`) and have
at least one test assert the fully formatted message, so the wording the user
guide promises is covered. This is a deliberately light contract until task
1.3.1 introduces the JSON envelope, at which point the template moves with it.

## Notes on what was checked and found sound

- **Command/query separation:** `make_stub_app` is a pure builder that returns
  an app (query); the entry points run the app (command). The split is clean
  and the load-bearing `*tokens` parameter is documented with the cyclopts
  version it was verified against.
- **Separation of concerns:** the deterministic spine keeps pure logic
  (`pure.py`) separate from the command surface (`commands/`), consistent with
  ADR-001's deterministic/judgemental boundary.
- **Documentation:** both the developer guide (§"The five commands") and the
  user guide (§"Installed Commands") were updated in the same slice and
  accurately describe the stub behaviour and exit code `2`.
- **Test coverage:** the in-process unit tests, the fast pyproject guard, and
  the slow end-to-end install test cover the success criterion thoroughly,
  including the cyclopts parser carve-outs (`--help`, `--version`, unknown
  option).
