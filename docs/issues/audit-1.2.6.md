# Post-merge audit — roadmap task 1.2.6

Audit of the codebase after roadmap task 1.2.6 ("Remove the dead `tomli_w`
snippet from `state-layout.md` and reconcile the premature 'is removed' claims")
merged to `main` at commit `2c19768`. Primary scope is the documentation and
code touched by that task: the rewritten initialization block in
[`skill/novel-ralph/references/state-layout.md`](../../skill/novel-ralph/references/state-layout.md),
the reconciled wording in
[`docs/adr-002-toml-round-trip-tomlkit.md`](../../docs/adr-002-toml-round-trip-tomlkit.md)
and [`docs/novel-ralph-harness-design.md`](../../docs/novel-ralph-harness-design.md),
and the new guard
[`tests/test_state_layout_reference.py`](../../tests/test_state_layout_reference.py).
The audit also re-checks whether the open items carried in
`docs/issues/audit-1.2.1.md` through `docs/issues/audit-1.2.5.md` have been
actioned.

The merged slice does what the roadmap asked. The dead `tomli_w` heredoc is gone
from the reference (the initialization step is now a `mkdir`/text block that
imports nothing), ADR-002 line 22 ("even carried a failed `tomli_w` snippet")
and line 77 ("is removed") now agree in tense and fact, and the design §5.3
wording matches. A new static guard pins the snippet's continued absence. Task
1.2.6 was a documentation-and-guard change, so the standing code findings from
the earlier audits carry forward unchanged — and this slice's new test module has
extended one of them by adding the fifth copy of a duplicated test constant.

Each finding below records a category, a location, a description, a concrete
proposed fix, and a severity. None is a blocking defect; they are tidy-up
opportunities plus prior-audit items that remain open and have grown by one copy
with this slice.

## Finding 1 — `_PROJECT_ROOT` is now redeclared in five test modules; the new guard adds the fifth

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`tests/test_state_layout_reference.py:23`](../../tests/test_state_layout_reference.py),
  [`tests/test_interrogate_gate.py:21`](../../tests/test_interrogate_gate.py),
  [`tests/test_command_names_registry.py:18`](../../tests/test_command_names_registry.py),
  [`tests/test_pyproject_scripts.py:17`](../../tests/test_pyproject_scripts.py),
  [`tests/test_console_scripts_e2e.py:39`](../../tests/test_console_scripts_e2e.py)

`_PROJECT_ROOT = Path(__file__).resolve().parent.parent` is now spelt
identically in five test modules. This slice's new
`tests/test_state_layout_reference.py` added the fifth copy rather than consuming
a shared home. This is the same shared-fixture gap audit-1.2.1 Finding 3 raised,
audit-1.2.4 Finding 2 carried, and audit-1.2.5 Finding 1 last counted at four:
there is still no `tests/conftest.py`, so every new test module that needs the
project root re-derives it. The drift risk per copy is low (the expression is
fixed), but the count is growing one-per-slice — the clearest possible signal
that the shared home is overdue.

**Proposed fix:** introduce `tests/conftest.py` (the home proposed since
audit-1.2.1 Finding 3) exposing a `project_root` fixture or module constant, and
have all five modules consume it. This is the same conftest that audit-1.2.3
Findings 1-2, audit-1.2.4 Finding 2, and audit-1.2.5 Findings 1-3 and 5 want for
the cuprum-catalogue helper, the `_venv_scripts_dir` resolver, the shared
`pyproject()` parse, and the `_table` accessor; landing it now, while the surface
is six modules, removes five copies in one move and gives the other deferred
helpers a place to live.

## Finding 2 — The new guard hand-rolls a sixth read-a-repo-file-and-parse helper rather than reusing a shared reader

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`tests/test_state_layout_reference.py:26`](../../tests/test_state_layout_reference.py)
  (`_state_layout_text`),
  [`tests/test_interrogate_gate.py:27`](../../tests/test_interrogate_gate.py)
  (`_pyproject`),
  [`tests/test_command_names_registry.py:21`](../../tests/test_command_names_registry.py)
  (`_parse_scripts`),
  [`tests/test_pyproject_scripts.py:22`](../../tests/test_pyproject_scripts.py)
  (inline `read_text(encoding="utf-8")`)

The new module adds `_state_layout_text()`, which builds a path under
`_PROJECT_ROOT` and reads it with `read_text(encoding="utf-8")` — the same
"resolve a repo-relative path off `_PROJECT_ROOT` and read it as UTF-8" step that
the three pyproject-reading guards (audit-1.2.5 Finding 2) already each
re-implement. The state-layout reader differs only in that it returns raw text
rather than a parsed TOML document, so it cannot fold onto the proposed
`pyproject()` helper directly, but it shares the path-resolution-and-read
boilerplate that the conftest is meant to own.

**Proposed fix:** when `tests/conftest.py` lands (Finding 1), expose a small
`read_repo_text(*parts)` (or a `repo_path(*parts)` joiner consumed with
`read_text`) helper rooted at the shared `project_root`, and have
`_state_layout_text` and the pyproject readers resolve their files through it.
This removes the repeated `_PROJECT_ROOT / ...` construction across the suite
and leaves each guard owning only its file-specific assertion.

## Finding 3 — `docs/contents.md` still omits ADR 006, the issues set, and the execplans set, and now lags one further audit

- **Category:** docs-gap
- **Severity:** low
- **Location:** [`docs/contents.md:17`](../../docs/contents.md) (the ADR
  section stops at ADR 005), and the absence of any entry for `docs/issues/` or
  `docs/execplans/`

audit-1.2.5 Finding 6 recorded that the documentation index lists ADRs 001-005
but not `docs/adr-006-console-scripts-e2e-posix-policy.md`, and has no entry for
the growing `docs/issues/` audit set or the `docs/execplans/` execution-plan set.
This slice did not touch `contents.md`, so all three gaps remain; the issues set
has since grown to six files (this audit included) and the execplans set to
twelve, widening the index's blind spot. A reader using `contents.md` as the map
still misses the POSIX-only policy and cannot discover the audit trail or the
per-task plans from the index.

**Proposed fix:** add ADR 006 to the "Architecture decision records" list in
`contents.md`, and add a short section (or two bullets) pointing at the
`docs/issues/` post-merge audit set and the `docs/execplans/` execution-plan set
so both are discoverable. This is index maintenance, not a restructuring; running
`make markdownlint` and `make nixie` over the edit suffices.

## Finding 4 — The state-layout guard pins only the `tomli_w` snippet, not the direct-edit pattern it modelled

- **Category:** test-gap
- **Severity:** low
- **Location:**
  [`tests/test_state_layout_reference.py:36`](../../tests/test_state_layout_reference.py)
  (`test_no_tomli_w_token`, `test_no_tomli_w_import_or_dump`),
  [`skill/novel-ralph/references/state-layout.md:218`](../../skill/novel-ralph/references/state-layout.md)
  (the "Discipline" block describing the write sequence in prose)

The new guard pins the absence of `tomli_w`, `tomllib, tomli_w`, and
`tomli_w.dump(`. This correctly catches a verbatim re-introduction of the deleted
heredoc, and the module docstring deliberately scopes the guard narrowly to avoid
colliding with roadmap task 6.2.3 (which owns pointing the reference prose at the
`novel-state` commands). The residual gap is that the snippet the slice removed
demonstrated a *behaviour* — hand-editing `state.toml` from a Python script with
an undeclared dependency — and the guard pins only the one library name that
behaviour happened to use. A contributor could reintroduce an equivalent
direct-edit recipe under a different writer (for example `tomlkit.dump(` in a
heredoc, or a `>> state.toml` shell append) without tripping any assertion, even
though design §4.1 rejects all direct `state.toml` editing, not just the
`tomli_w` form.

**Proposed fix:** no change is required at this commit — broadening the guard now
would collide with task 6.2.3 as the docstring notes, and the prose still
describes the manual write sequence that 6.2.3 will replace with a pointer at
`novel-state`. Record the decision to keep the guard `tomli_w`-specific until
6.2.3, and have 6.2.3 (which rewrites the reference prose to call the commands)
widen this guard to assert the reference contains no direct-`state.toml`-write
recipe at all, so the absence of the *pattern*, not just the one dead library, is
pinned once the prose no longer needs the manual sequence.

## Notes on what was checked and found sound

- **The roadmap objective is met.** The dead `tomli_w` heredoc is gone from
  `state-layout.md`; the initialization step is now a `mkdir`/text block that
  imports nothing. ADR-002 line 22 ("even carried a failed `tomli_w` snippet",
  past tense) and line 77 ("the failed `tomli_w` snippet is removed", present
  tense) are now consistent rather than contradictory, and design §5.3 line 466
  ("The failed `tomli_w` snippet in the reference is removed") agrees. The
  premature-removal-claim defect that review:1.2.2 raised is resolved.
- **The guard is honest and well-scoped.** `test_state_layout_reference.py`
  parses statically with `pathlib` rather than shelling out, pins three distinct
  tokens (the bare name, the comma-form import, and the `.dump(` call site), and
  documents in its docstring exactly why it stays substring-specific (to avoid
  colliding with task 6.2.3). The two test methods carry clear docstrings and the
  module stays at 100% docstring coverage, so the new interrogate gate holds.
- **No new command/query concern.** `_state_layout_text` is a pure query; the
  only side effects are pytest assertions. The slice introduced no production
  code, so the deterministic-versus-judgemental boundary (ADR-001) is untouched.
- **The `plan.md` reference is correctly left alone.** The dead per-chapter
  `plan.md` reference at `state-layout.md:38` and the `plan/` directory mentions
  (lines 32, 235) are owned by roadmap tasks 2.1.1 and 6.2.3, not by 1.2.6, so
  this slice rightly did not touch them. They are recorded here only to confirm
  the scope boundary was respected.
- **Prose conventions.** The slice's prose follows en-GB Oxford spelling, and the
  `AGENTS.md` quality gates (`make all`, `make markdownlint`, `make nixie`) pass
  on the merged change.
