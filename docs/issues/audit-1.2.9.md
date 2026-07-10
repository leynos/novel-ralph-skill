# Post-merge audit — roadmap task 1.2.9

Audit of the codebase after roadmap task 1.2.9 ("Tighten the `read_repo_text`
fixture signature from `Callable[..., str]` to a precise `(*parts: str) -> str`
form") merged to `main` as commit `39a06b4`.

The slice itself is sound: it introduced a named `RepoTextReader` `Protocol`
inside the `TYPE_CHECKING` block of [`tests/conftest.py`](../../tests/conftest.py),
returned it from the `read_repo_text` fixture, added a multi-part-join unit test,
and carved a narrow, well-justified `TYPE_CHECKING`-import exception into
[`docs/developers-guide.md`](../developers-guide.md). The `ty` typecheck, Ruff,
`interrogate`, and Pylint gates all govern the changed file, and the prose
exception is precise about why a type-only import does not reintroduce the
cross-module-import fragility the convention guards against.

The findings below are tidy-up opportunities, not blocking defects. Finding 1 is
the natural follow-on the 1.2.9 design left incomplete and is newly raised here;
the remainder are carried from earlier audits and confirmed still open after
1.2.9.

## Finding 1 — The Protocol-vs-`Callable` tightening was applied to one fixture only; four sibling fixtures keep verbose inline `Callable` annotations duplicated at every call site

- **Category:** inconsistency
- **Severity:** low
- **Location:**
  [`tests/conftest.py:116-223`](../../tests/conftest.py)
  (the `toml_table`, `dist_name`, `single_program_catalogue`, and
  `venv_scripts_dir` fixtures), and their consuming call sites —
  [`tests/test_conftest_helpers.py`](../../tests/test_conftest_helpers.py),
  [`tests/test_interrogate_gate.py`](../../tests/test_interrogate_gate.py),
  [`tests/test_contract_test_deps.py`](../../tests/test_contract_test_deps.py),
  [`tests/test_command_names_registry.py`](../../tests/test_command_names_registry.py),
  and [`tests/test_pyproject_scripts.py`](../../tests/test_pyproject_scripts.py)

Task 1.2.9's stated rationale was that the `...` wildcard in `Callable[..., str]`
"disables per-call argument-shape checking", and it fixed this for `read_repo_text`
by replacing the `Callable` with a named `Protocol`. That rationale is not unique
to `read_repo_text`. The four remaining callable-valued fixtures keep their types
spelled inline as `cabc.Callable[...]`, and those spellings are then re-typed by
hand at every consuming parameter:

- `cabc.Callable[[cabc.Mapping[str, object], str], dict[str, object]]`
  (`toml_table`) appears **11 times across 6 files**.
- `cabc.Callable[[str], str | None]` (`dist_name`) appears **4 times across 4
  files**.
- `cabc.Callable[[str, Program], ProgramCatalogue]`
  (`single_program_catalogue`) and `cabc.Callable[[Path], Path]`
  (`venv_scripts_dir`) are each re-spelled at their call sites too.

This is a duplication and inconsistency seam: the long structural annotation is
copied verbatim into every test that consumes the fixture, so a future signature
change (for example, `toml_table` gaining a default or `dist_name` returning a
richer type) must be edited at every call site by hand, and a typo in one copy
silently weakens checking there. It also leaves the suite half-converted —
`read_repo_text` reads as a named type while its siblings read as raw structural
`Callable`s, so a maintainer cannot tell from the annotation whether a precise
shape was intended.

**Proposed fix:** finish the conversion the 1.2.9 design began. Either (a) define
the remaining fixture return types as named `Protocol`s (`TomlTableAccessor`,
`DistNameNormaliser`, `SingleProgramCatalogueBuilder`, `VenvScriptsResolver`) in
the `TYPE_CHECKING` block alongside `RepoTextReader`, returning them from the
fixtures and importing them under the documented `TYPE_CHECKING` exception at the
call sites; or (b) at minimum, hoist each verbose `Callable[...]` into a single
`type`-statement alias in `conftest.py` (`type TomlTableAccessor = ...`) imported
the same way, so the structural shape lives once. Option (a) is the more faithful
continuation of 1.2.9 because it restores per-call argument-shape checking for
the `single_program_catalogue` builder in the same spirit. `make test` plus the
`ty`/Ruff gates cover the change. This is a natural candidate for its own small
roadmap remediation under step 1.2.

## Finding 2 — The `render_human` empty-messages branch is still unexercised (carried)

- **Category:** test-gap
- **Severity:** medium
- **Location:**
  [`novel_ralph_skill/contract/envelope.py:169-170`](../../novel_ralph_skill/contract/envelope.py)
  (the `else` arm emitting `messages: (none)`),
  [`tests/test_contract_envelope.py`](../../tests/test_contract_envelope.py)

First raised as `audit-1.2.10.md` Finding 1, carried through `audit-1.2.11.md`
Finding 3, and confirmed still open after 1.2.9. Every test that calls
`render_human` (`test_render_human_lists_messages_without_result_json` and
`test_render_human_success_snapshot`) passes a non-empty `messages` sequence, so
the `if env.messages:` branch is always taken and the `else` arm that emits the
literal `messages: (none)` line for a message-less envelope is never exercised.
The three `messages=[]` cases in `test_contract_envelope.py` drive
`build_envelope`/`render_machine`, not `render_human`. A message-less success
envelope is a real, expected shape (a satisfied checker with nothing to say), so
the unrendered branch is exactly the path a future edit could break unnoticed.

**Proposed fix:** add a focused test that builds an envelope with `messages=[]`
and asserts `render_human(env)` contains the literal `messages: (none)` line and
does not contain a two-space-and-dash message bullet; a syrupy snapshot of the
empty-messages rendering would also pin the exact line. `make test` over the new
case suffices.

## Finding 3 — A third copy of the wrapper-configured Cyclopts app builder persists (carried)

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`tests/test_contract_runner.py`](../../tests/test_contract_runner.py)
  (`_build_app`),
  [`tests/test_contract_properties.py`](../../tests/test_contract_properties.py)
  (`_build_app`),
  [`tests/test_cyclopts_contract.py`](../../tests/test_cyclopts_contract.py)
  (`_make_app`)

Carried from `audit-1.2.8.md` Finding 3, `audit-1.2.10.md` Finding 2, and
`audit-1.2.11.md` Finding 4; untouched by 1.2.9. Three test modules each build a
Cyclopts app with the same load-bearing
`result_action="return_value", exit_on_error=False, print_error=False,
help_on_error=False` configuration the `run` wrapper requires. A future cyclopts
upgrade that changes one of those keyword defaults must be re-discovered and
re-fixed three times.

**Proposed fix:** roadmap task 1.2.21 already covers extracting a shared
wrapper-app builder fixture into `tests/conftest.py`. No new roadmap item is
needed; flagged only to record that 1.2.9 did not touch it.

## Finding 4 — `STUB_EXIT_CODE` re-spells the contract's usage-error code as a bare literal (carried)

- **Category:** inconsistency
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/commands/stub.py:18`](../../novel_ralph_skill/commands/stub.py)
  (`STUB_EXIT_CODE = 2`),
  [`novel_ralph_skill/contract/exit_codes.py:26`](../../novel_ralph_skill/contract/exit_codes.py)
  (`ExitCode.USAGE_ERROR = 2`)

Carried from `audit-1.2.10.md` Finding 6 and `audit-1.2.11.md` Finding 5. The
stub module defines `STUB_EXIT_CODE = 2` with a docstring naming it "usage error,
design 3.2", which is exactly `ExitCode.USAGE_ERROR`. The contract package now
exists as the single source of truth for the exit-code vocabulary, yet the stub
hard-codes the integer `2` independently. If a future contract revision
renumbered the usage-error code, the stubs would silently diverge.

**Proposed fix:** import `ExitCode` from
`novel_ralph_skill.contract.exit_codes` and define
`STUB_EXIT_CODE = ExitCode.USAGE_ERROR` (or use the enum member directly in the
`sys.exit` call). Because `ExitCode` subclasses `int`, behaviour is unchanged.
Best sequenced when the stubs adopt the envelope contract (roadmap 1.3.x) so they
migrate in one move.

## Finding 5 — Four near-identical locked-version-pin guards lack a shared shape (carried)

- **Category:** similarity
- **Severity:** low
- **Location:**
  [`tests/test_tomlkit_dependency.py`](../../tests/test_tomlkit_dependency.py)
  (`LOCKED_TOMLKIT_VERSION`),
  [`tests/test_cyclopts_contract.py`](../../tests/test_cyclopts_contract.py)
  (`LOCKED_CYCLOPTS_VERSION`),
  [`tests/test_contract_test_deps.py`](../../tests/test_contract_test_deps.py)
  (`LOCKED_HYPOTHESIS_VERSION`, `LOCKED_SYRUPY_VERSION`)

Carried from `audit-1.2.11.md` Finding 6. Four locked-version tripwires follow
the same pattern: a `LOCKED_X_VERSION` constant and an assertion that the
resolved version (via `module.__version__` or `importlib.metadata.version`)
equals the pin. The bodies differ just enough to read as a similarity rather than
a clean duplication, but as the spine grows more pinned dependencies the shape is
worth consolidating.

**Proposed fix:** introduce a shared `assert_locked_version(dist, expected)`
helper (or a parametrized fixture) in `tests/conftest.py` that resolves a version
through `importlib.metadata.version` and asserts it, letting each module keep only
its `(distribution, pin)` pair. Not yet a roadmap item; flagged for tracking.

## Notes on what was checked and found sound

- The `RepoTextReader` `Protocol` and its `__call__` signature are correctly
  confined to the `TYPE_CHECKING` block, so they add no runtime import cost; the
  three consuming modules import the type under their own `TYPE_CHECKING` guard,
  matching the documented exception.
- The contract package (`envelope.py`, `exit_codes.py`, `runner.py`) keeps a
  clean command/query separation: `build_envelope`/`render_*`/`is_ok` are pure
  queries, and `run`/`_emit` own the side effects (stdout, `sys.exit`). No
  command-query segregation violation was found there.
- `COMMAND_ENTRY_POINTS` remains the single source of truth for command names,
  consumed by `stub.py`, the envelope validator, and the scripts-table gate; no
  new name duplication was introduced.
- Docstring coverage is at the 100% `interrogate` standard across the changed
  files; the developers-guide change is internally consistent and en-GB.
