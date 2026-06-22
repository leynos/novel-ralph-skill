# Post-merge audit — roadmap task 1.2.8

Audit of the codebase after roadmap task 1.2.8 ("Broaden state-layout
direct-edit guard to reject any hand-edit recipe") merged to `main` at commit
`011de15`. Primary scope is the slice's centrepiece —
[`tests/test_state_layout_reference.py`](../../tests/test_state_layout_reference.py),
rewritten from a `tomli_w`-substring guard into a CommonMark fence scanner — and
the developers' guide section that documents it
([`docs/developers-guide.md`](../../docs/developers-guide.md) §"The state-layout
direct-edit guard"). The audit also re-checks whether the open items carried in
`docs/issues/audit-1.2.1.md` through `docs/issues/audit-1.2.7.md` have been
actioned by this slice.

The merged slice does what the roadmap asked, and it does it well. The fence
scanner is a set of pure functions over markdown text, each with a docstring and
a clear rationale comment; the planted-recipe matrix covers seventeen forbidden
forms (library writers, `open(...)` write modes, shell redirects and heredocs,
`tee`/`tee -a`, tilde and quad-backtick fences, indented list-step fences, and an
unknown-writer `.write(` backstop) and the negative matrix pins six clean forms
(atomic-write prose, read-only `open(..., "rb")`, a `pycon` read-only transcript,
unrelated redirects, a `novel-state` example, and a non-executable `toml` fence).
The guard reads the reference through the shared `read_repo_text` fixture, so it
inherits the conftest consolidation rather than re-rolling a reader. The
state-layout reference itself is currently clean: its fences are all
`text`/`toml`/`markdown`, so the guard's subject carries no recipe to flag.

The 1.2.7 markdownlint MD012 regression (audit-1.2.7 Finding 4) is **fixed**:
`docs/developers-guide.md` line 19 now carries a single blank line, so
`make markdownlint` is green on `main` again.

The residual findings below are: two documentation inaccuracies the 1.2.8 slice
introduced in the guide's description of the new guard; one test-helper
duplication landed alongside the 1.3.1 contract module; and four prior-audit
items the 1.2.8 slice did not touch and which remain open. None is a blocking
defect. Each finding records a category, a location, a description, a concrete
proposed fix, and a severity.

## Finding 1 — The developers' guide write-token list is stale relative to the merged guard

- **Category:** inconsistency
- **Severity:** medium
- **Location:**
  [`docs/developers-guide.md:207-210`](../../docs/developers-guide.md) (the
  "known TOML writer (`tomlkit.dump`, `tomli_w`, `.write_text`)" parenthetical),
  [`tests/test_state_layout_reference.py:93`](../../tests/test_state_layout_reference.py)
  (`_LIBRARY_WRITE_TOKENS`)

The 1.2.8 slice broadened `_LIBRARY_WRITE_TOKENS` to five entries —
`tomlkit.dump`, `tomli_w`, `.write_text(`, `.write_bytes(`, `.writelines(` — and
added the `.write_bytes(` planted-recipe row (`path-write-bytes`) precisely so a
binary TOML write to the state file is caught. But the developers' guide section
that documents the guard still enumerates only three library writers
("`tomlkit.dump`, `tomli_w`, `.write_text`"), omitting `.write_bytes` and
`.writelines`. The guide is the orientation a contributor reads before the test,
so a maintainer reading the prose would believe a `Path(...).write_bytes(...)`
recipe slips past the guard when in fact it is caught — the doc understates the
guard's reach, which is the inverse of the usual drift but equally misleading.

**Proposed fix:** update the parenthetical at `docs/developers-guide.md:208` to
list all five library writers the guard recognises (`tomlkit.dump`, `tomli_w`,
`.write_text`, `.write_bytes`, `.writelines`), so the prose matches
`_LIBRARY_WRITE_TOKENS`. Optionally add a one-clause note that the list is the
documented mirror of that tuple, so a future broadening updates both in lockstep.
Fold this into the next documentation-touching slice; `make markdownlint` and
`make nixie` over the edit suffice.

## Finding 2 — The developers' guide executable-fence list omits `python3`, `py3`, and `pycon`

- **Category:** inconsistency
- **Severity:** low
- **Location:**
  [`docs/developers-guide.md:207`](../../docs/developers-guide.md) (the
  "executable code fences (`python`/`py`/`sh`/`bash`/`shell`/`console`)"
  parenthetical),
  [`tests/test_state_layout_reference.py:44-56`](../../tests/test_state_layout_reference.py)
  (`_PYTHON_INFO_STRINGS` and `_EXECUTABLE_INFO_STRINGS`)

The guard's executable info-string set is
`{python, python3, py, py3, pycon, sh, bash, shell, console}` — nine labels,
with `python3`/`py3`/`pycon` carried in `_PYTHON_INFO_STRINGS`. The
`python3-raw-open-write` planted row and the `pycon` read-only negative test both
depend on those labels being scanned. The developers' guide lists only six
(`python`/`py`/`sh`/`bash`/`shell`/`console`), dropping the three Python-variant
labels. A reader reconciling the prose against the test would find three info
strings in the code that the documentation does not mention, and might assume a
`python3` or `pycon` fence is exempt.

**Proposed fix:** extend the guide's info-string list at
`docs/developers-guide.md:207` to include `python3`, `py3`, and `pycon` (or
reword to "the Python-flavoured and shell info strings" with the canonical set
named once), so the documented set matches `_EXECUTABLE_INFO_STRINGS`. Pair this
with Finding 1 in the same guide edit, since both correct the same paragraph.

## Finding 3 — `_build_app` is duplicated across the two contract `run`-driver test modules

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`tests/test_contract_runner.py:32`](../../tests/test_contract_runner.py)
  (`_build_app`),
  [`tests/test_contract_properties.py:131`](../../tests/test_contract_properties.py)
  (`_build_app`)

Both contract test modules define a private `_build_app(outcome)` that builds a
Cyclopts app with the identical four-flag configuration
(`result_action="return_value", exit_on_error=False, print_error=False,
help_on_error=False`) and a single `act` subcommand that returns the configured
outcome or raises `StateInputError`. The two copies differ only cosmetically:
`test_contract_runner` gives `act` an unused `name` parameter and defaults
`outcome` to a success outcome, while `test_contract_properties` takes a required
`outcome`. This is the same app-construction intent spelt twice, landed together
in roadmap task 1.3.1, and it is exactly the kind of test-helper duplication the
conftest consolidation (task 1.2.7) was built to absorb. The four-flag
configuration is load-bearing (a missing flag silently changes the exit path), so
two copies are two places to keep that contract correct.

**Proposed fix:** lift a `wrapper_app` (or `build_wrapper_app`) fixture into
[`tests/conftest.py`](../../tests/conftest.py) returning a
`(outcome: CommandOutcome | None) -> cyclopts.App` builder that constructs the
four-flag app with the `act` subcommand, and have both modules consume it by
fixture name. This removes the second copy and makes the load-bearing flag set
live once. If the `name`-parameter variant is still wanted for the
extra-positional-token usage-error case, keep that single difference local to the
one test that needs it rather than duplicating the whole builder.

## Finding 4 — `test_contract_test_deps.py` was not migrated onto the shared conftest fixtures (carried from audit-1.2.7 Finding 1)

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`tests/test_contract_test_deps.py:30`](../../tests/test_contract_test_deps.py)
  (`_PYPROJECT`),
  [`tests/test_contract_test_deps.py:33`](../../tests/test_contract_test_deps.py)
  (`_dev_dependencies`),
  [`tests/conftest.py:47`](../../tests/conftest.py) (the `pyproject` fixture),
  [`tests/conftest.py:87`](../../tests/conftest.py) (the `toml_table` fixture)

audit-1.2.7 Finding 1 recorded that `test_contract_test_deps` is the seventh
test module reading `pyproject.toml` and the one the conftest migration did not
reach, because it landed on the parallel 1.3.1 branch. The 1.2.8 slice touched
neither module, so the finding is unchanged: `test_contract_test_deps` still
computes
`_PYPROJECT = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"`
and parses it with `tomllib.loads(...)` inside `_dev_dependencies`, rather than
taking the `pyproject` and `toml_table` fixtures the conftest now owns.

**Proposed fix:** as audit-1.2.7 proposed — migrate the dev-dependency tests onto
the shared fixtures, reading the dev group as
`toml_table(pyproject, "dependency-groups")["dev"]`, and delete `_PYPROJECT` and
`_dev_dependencies`. The two version-pin tests read installed distribution
metadata rather than `pyproject.toml`, so they stay as they are.

## Finding 5 — Dependency-name normalisation is duplicated and the two copies disagree (carried from audit-1.2.7 Finding 2)

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`tests/test_interrogate_gate.py:24`](../../tests/test_interrogate_gate.py)
  (`_DIST_NAME` regex and `_dist_name`),
  [`tests/test_contract_test_deps.py:79`](../../tests/test_contract_test_deps.py)
  (the inline `spec.split()[0].split(">")[0].split("=")[0]` expression)

audit-1.2.7 Finding 2 recorded that two modules independently normalise a PEP 508
requirement string to its bare distribution name, and that the two copies
disagree on correctness: `test_interrogate_gate`'s documented `_DIST_NAME` regex
correctly stops at the first non-name character (so it handles extras such as
`interrogate[toml]` and version specifiers), while `test_contract_test_deps`'s
inline `spec.split()[0].split(">")[0].split("=")[0]` splits only on whitespace,
`>`, and `=`, so an extras form like `hypothesis[cli]` or a `~=`/`<` specifier
would leak the bracket or operator into the "name". The 1.2.8 slice touched
neither, so both copies — and the divergence — remain.

**Proposed fix:** as audit-1.2.7 proposed — lift the requirement-name normaliser
into `tests/conftest.py` as a fixture (for example `dist_name` returning a
`(spec: str) -> str | None` callable backed by the `_DIST_NAME` regex), and have
both `test_interrogate_gate` and `test_contract_test_deps` consume it. This
removes the second copy and replaces the weaker `split`-chain with the regex that
already handles extras and markers. Pair it with Finding 4 so the contract-deps
module reaches the shared home in one move.

## Finding 6 — `test_command_names_registry` keeps a private `_parse_scripts` rather than a shared scripts accessor (carried from audit-1.2.7 Finding 3)

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`tests/test_command_names_registry.py:21`](../../tests/test_command_names_registry.py)
  (`_parse_scripts`),
  [`tests/test_pyproject_scripts.py`](../../tests/test_pyproject_scripts.py)
  (the inline `toml_table(toml_table(pyproject, "project"), "scripts")`)

audit-1.2.7 Finding 3 recorded that both modules narrow `pyproject` down to
`[project.scripts]`, one via a module-private `_parse_scripts` wrapper and the
other inline, spelling the same nested-table access two ways. The 1.2.8 slice
touched neither, so the seam remains.

**Proposed fix:** as audit-1.2.7 proposed — expose a small
`project_scripts(pyproject)` fixture in `tests/conftest.py` (or a general
`toml_path(pyproject, *keys)` walker chaining `toml_table` over a key sequence)
and have both modules consume it, deleting `_parse_scripts`. Low cost to leave;
recording it keeps the conftest the single home for table navigation.

## Finding 7 — `docs/contents.md` still omits ADR 006, the issues set, and the execplans set (carried from audit-1.2.5 Finding 6, audit-1.2.6 Finding 3, audit-1.2.7 Finding 5)

- **Category:** docs-gap
- **Severity:** low
- **Location:** [`docs/contents.md:28`](../../docs/contents.md) (the
  "Architecture decision records" list stops at ADR 005), and the absence of any
  entry for `docs/issues/` or `docs/execplans/`

The documentation index lists ADRs 001-005 but not
[`docs/adr-006-console-scripts-e2e-posix-policy.md`](../../docs/adr-006-console-scripts-e2e-posix-policy.md),
and has no entry for the `docs/issues/` post-merge audit set or the
`docs/execplans/` execution-plan set. The 1.2.8 slice did not touch
`contents.md`, so all three gaps remain and the blind spot has widened again:
the issues set is now eight files (this audit included) and the execplans set is
twenty. A reader using `contents.md` as the map still misses the POSIX-only
console-scripts policy and cannot discover the audit trail or the per-task
execution plans from the index. ADR 003 is now cited throughout the developers'
guide for the landed envelope contract, which makes the missing ADR 006 entry
more conspicuous, not less.

**Proposed fix:** as the three prior audits proposed — add ADR 006 to the
"Architecture decision records" list, and add a short section (or two bullets)
pointing at the `docs/issues/` post-merge audit set and the `docs/execplans/`
execution-plan set so both are discoverable. This is index maintenance, not a
restructuring; running `make markdownlint` and `make nixie` over the edit
suffices. Small enough to fold into whichever slice next touches the index.

## Notes on what was checked and found sound

- **The roadmap objective is met.** The guard now scans every executable code
  fence for a write primitive rather than matching the lone historical `tomli_w`
  substring. The fence regex honours CommonMark (backtick and tilde fences, runs
  of three-or-more with a back-referenced closing run, up to three leading
  spaces of indentation, and an info string that excludes the fence character),
  and `_dedent_fence_body` mirrors CommonMark's indentation stripping so a
  list-nested recipe is scanned identically to a flush-left one. The named
  `tomli_w` regression assertions are retained alongside the broadened scanner.
- **The scanner is well-factored and pure.** `_iter_executable_fences`,
  `_dedent_fence_body`, `_write_token`, and `find_direct_state_write_recipes`
  are pure functions over markdown text taking the document as a parameter; none
  shells out, imports `novel_ralph_skill`, or reads any file other than through
  the shared `read_repo_text` fixture. Each rule is anchored to the `state.toml`
  path, never redirect-anywhere, and the `(?<!>)` guard keeps a `>>>` REPL
  prompt from being read as a `>>` append operator.
- **The planted/negative matrices are honest.** Seventeen forbidden forms are
  each asserted flagged and six clean forms are each asserted not flagged,
  including the subtle cases (no-space redirects, `tee -a`, indented list steps,
  a `pycon` read-only transcript, and a non-executable `toml` fence). The
  positive and negative pairs guard against both a loosened path anchor and an
  over-broad write rule.
- **The MD012 regression is fixed.** `docs/developers-guide.md` no longer carries
  the double blank line audit-1.2.7 Finding 4 flagged; `make markdownlint` is
  green on `main`.
- **No command/query or boundary concern.** The slice introduced no production
  code; the guard is a read-only query over a documentation file, and the
  deterministic-versus-judgemental boundary (ADR-001) is untouched.
- **Prose conventions.** The slice's docstrings and guide prose follow en-GB
  Oxford spelling; the new guide section is accurate apart from the two
  enumeration gaps recorded as Findings 1 and 2.
