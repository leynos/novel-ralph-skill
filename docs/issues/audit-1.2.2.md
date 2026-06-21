# Post-merge audit — roadmap task 1.2.2

Audit of the codebase after roadmap task 1.2.2 ("Add `tomlkit` to the package
dependencies and confirm the build") merged to `main` at commit `183d913`.
Primary scope is the code and documentation introduced or touched by that task:
the `tomlkit` dependency in `pyproject.toml`, the locked version in `uv.lock`,
and the new dependency-confirmation test
(`tests/test_tomlkit_dependency.py`). The audit also re-checks whether the
findings recorded against task 1.2.1 (`docs/issues/audit-1.2.1.md`) have been
actioned, since the surface is still small enough that carrying them forward is
cheap.

Each finding records a category, a location, a description, a concrete proposed
fix, and a severity. None of these are blocking defects; the merged slice is
correct, well tested, and well documented. They are tidy-up opportunities and
one documentation-accuracy correction to action before the state slice (task
2.2.1) builds on this dependency.

## Finding 1 — Design §5.3 and ADR-002 claim a snippet "is removed" that is still present

- **Category:** docs-gap
- **Severity:** medium
- **Location:** `docs/novel-ralph-harness-design.md:464`
  ("The failed `tomli_w` snippet in the current reference is removed."),
  `docs/adr-002-toml-round-trip-tomlkit.md:77` ("the failed `tomli_w` snippet
  is removed from the reference material"), versus the still-present snippet at
  `skill/novel-ralph/references/state-layout.md:229` and `:235`

ADR-002 and design §5.3 — the two documents that justify the `tomlkit`
dependency this task added — both state in the present tense that the failed
`tomli_w` snippet has been removed from the reference material. It has not. The
snippet still imports `tomli_w` and calls `tomli_w.dump(...)` in the
`state-layout.md` state-mutation example. The terms of reference
(`docs/terms-of-reference.md:39`) correctly describe `tomli_w` as an undeclared
dependency that does not run, so the design and ADR are the documents out of
step with the tree. The task 1.2.2 execplan
(`docs/execplans/roadmap-1-2-2.md`) flagged this explicitly and correctly
scoped it out, because the dependency-addition task owns no skill-reference
edits.

The risk: a reader trusting the design or the ADR believes the reference is
clean and may copy the `tomli_w` pattern that this whole ADR exists to reject.
The removal is also genuinely unassigned in the roadmap (see the proposed
roadmap item below): task 6.2.3 enumerates three skill-defect fixes — the
`SKILL.md:107` phase mislabel, the duplicated done-predicate prose, and the
dead `state-layout.md:38` `plan.md` reference — and the `tomli_w` snippet is
none of them.

**Proposed fix:** assign the snippet removal to a roadmap task (6.2.3 is the
natural home, as it already owns `state-layout.md` corrections) and, in the
same change, either delete the `tomli_w` example or rewrite it to use
`tomlkit`. Until that lands, soften the design §5.3 and ADR-002 wording from
the present-tense "is removed" to a forward-looking "is removed in roadmap task
6.2.3", so the documents stop asserting a state the tree does not yet hold.

## Finding 2 — `tomlkit` is unpinned in `pyproject.toml` but the test asserts an exact version

- **Category:** inconsistency
- **Severity:** low
- **Location:** `pyproject.toml:8` (`dependencies = ["cyclopts", "tomlkit"]`),
  `tests/test_tomlkit_dependency.py:24`
  (`LOCKED_TOMLKIT_VERSION = "0.15.0"`), `uv.lock:640` (`version = "0.15.0"`)

`tomlkit` is declared without a version constraint, while
`test_tomlkit_import_and_version` asserts the installed version equals exactly
`0.15.0`. The two are reconciled today only by `uv.lock`, which pins `0.15.0`.
This is a deliberate tripwire design — the test docstring explains it guards
against a silent re-resolution past the major-version round-trip risk named in
ADR-002 "Known risks" — and it is sound while the lockfile is the contract.
The mild awkwardness is that the contract lives in three places (loose
declaration, locked resolution, hard-coded test constant) with no single
comment in `pyproject.toml` pointing a maintainer at the test that will break
if they bump the dependency. A `uv lock --upgrade` would re-resolve `tomlkit`
and fail the version assertion with no breadcrumb at the declaration site
explaining why.

**Proposed fix:** add a short comment beside the `tomlkit` entry in
`pyproject.toml` noting that the exact version is pinned in `uv.lock` and
asserted by `tests/test_tomlkit_dependency.py::test_tomlkit_import_and_version`,
so a maintainer bumping the dependency knows to update the test constant in
lockstep. Optionally add a lower-bound constraint (for example
`tomlkit>=0.15`) to make the floor explicit while leaving the exact pin to the
lockfile. Do not remove the version assertion: it is the regression guard the
ADR relies on until the round-trip property test (task 2.2.1) exists.

## Finding 3 — Dependency-confirmation test overlaps the planned 2.2.1 round-trip property

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/test_tomlkit_dependency.py:42`
  (`test_tomlkit_roundtrip_is_lossless`), `:53`
  (`test_tomlkit_edit_preserves_comments`)

The new test proves `tomlkit` round-trips and comment-preserves over a small,
hand-written TOML fragment (`SRC`). This is exactly right for a
dependency-confirmation check and the docstring is careful to say so. The gap
is forward-looking: the real property — a no-op read-mutate-write that
preserves an actual `state.toml` byte-for-byte, integrated with the atomic
temp-file-and-`Path.replace` write discipline — is deferred to task 2.2.1
(design §9, ADR-002 functional and technical requirements). Nothing here is
wrong, but there is a latent risk that the two tests are later seen as
overlapping and the 2.2.1 property is trimmed because "round-trip is already
tested", losing the property-based coverage over generated states and the
atomic-write integration that the ADR's technical requirements actually demand.

**Proposed fix:** no change to this task's test. When task 2.2.1 lands, add a
one-line cross-reference comment in `test_tomlkit_dependency.py` pointing at
the 2.2.1 property test, and ensure the 2.2.1 test explicitly covers the two
things this one does not — property-based generation over realistic state
shapes and the atomic-write path — so the distinction between
"dependency resolves and round-trips a fragment" and "the mutator preserves a
real state file atomically" is recorded rather than rediscovered.

## Finding 4 — Prior-audit duplication and gating findings remain unactioned

- **Category:** duplication
- **Severity:** low
- **Location:** `tests/test_command_stubs.py:23`,
  `tests/test_console_scripts_e2e.py:47`,
  `tests/test_pyproject_scripts.py:17` (three independent copies of the five
  command names); no `tests/conftest.py`; `pyproject.toml:20`
  (`interrogate` is a dev dependency with no `[tool.interrogate]` block and no
  Makefile target)

The findings recorded against task 1.2.1
(`docs/issues/audit-1.2.1.md`, findings 1, 3, and 4) are still open at this
commit. The five command names are still hand-written across three test
modules and the stub module; there is still no `tests/conftest.py` to host a
shared command-name fixture or a project-root fixture; and `interrogate` is
still installed but unconfigured and ungated, so docstring coverage is not
enforced despite the new modules being well documented. None of these is
introduced by task 1.2.2, but each compounds slightly as the surface grows, and
the cheapest moment to fix the duplication and lock in the docstring gate is
while the command surface is still five thin stubs.

**Proposed fix:** action audit-1.2.1 findings 1, 3, and 4: introduce a single
command-name registry in `novel_ralph_skill.commands.stub` and derive the test
fixtures from it via a new `tests/conftest.py`; and add a `[tool.interrogate]`
block with an explicit `fail-under` threshold wired into the lint gate (or
remove `interrogate` from the dev group if the gate is intentionally deferred).
Folding these into the task 2.2.1 slice, which already touches the command
surface, keeps the change set coherent.

## Notes on what was checked and found sound

- **Dependency wiring:** `tomlkit` is correctly added to
  `[project].dependencies`, resolved in `uv.lock` to `0.15.0` with hashes, and
  exercised by `make test` through the new module. The declaration is
  load-bearing and proven so by the import-and-version test.
- **Test design:** the three new test functions are pure queries with no
  side effects, each carries a numpy-style docstring with a `Returns` section,
  and the module docstring correctly scopes the check to a fragment rather than
  `state.toml`, deferring the real property to task 2.2.1. No command/query
  separation concern.
- **Round-trip behaviour:** the lossless no-op and the
  comment-preserving edit are both asserted, which is the minimum that proves
  the dependency does what ADR-002 selected it for.
- **Quality gates:** the change passes the AGENTS.md gates (`make all`), and
  the prose follows the en-GB Oxford-spelling convention.
