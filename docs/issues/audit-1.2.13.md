# Post-merge audit: roadmap task 1.2.13

Audit of the codebase following the merge of roadmap task 1.2.13, "Migrate e2e
and contract suites to invoke `novel <sub>`" (commit `17f3c8b`). The change
re-points the installed-binary e2e suites and the per-chapter-loop installed BDD
steps from the legacy five console-scripts (`novel-state`, `desloppify`, …) onto
the single `novel` multiplexer with a spaced subcommand surface (`novel state`,
`novel desloppify`, …). It is additive: the legacy `[project.scripts]` entries
and the `COMMAND_NAMES` / `COMMAND_ENTRY_POINTS` registry symbols stay in place
(removed in task 1.2.15) so the legacy-vs-multiplexer parity tests retain their
oracle.

Scope of the merged change: `tests/installed_binary_fixtures.py`,
`tests/steps/per_chapter_loop_installed_steps.py`,
`tests/test_installed_command_names.py` (new), and the eleven `tests/test_*_e2e`
and contract modules listed in the commit stat. No production module changed.

Trail followed: `docs/roadmap.md` tasks 1.2.12-1.2.15;
`docs/adr-007-command-surface-novel-multiplexer.md`;
`docs/novel-ralph-harness-design.md` §4; `docs/developers-guide.md` "Shared test
scaffolding"; `docs/users-guide.md` "Installed Commands"; `AGENTS.md` code-style,
refactoring-heuristics, and quality-gate rules. Explored with `leta`
(`show`/`grep`/`refs`) over `novel_ralph_skill/commands/` and the test tree, and
traced history with `git show 17f3c8b`.

Findings are listed by severity. None block the merge; all are tidy-up,
consistency, or doc-debt items suitable for an addendum or follow-on lane. Note
that some findings are partly discharged by the already-planned tasks 1.2.14
(design and `SKILL.md` sweep) and 1.2.15 (legacy-surface removal); each finding
records the overlap so the triage agent can avoid double-scheduling.

## Finding 1: Installed-script run boilerplate is duplicated across the e2e suite (medium)

- **Category:** duplication
- **Location:** `tests/test_recount_e2e.py:128-132`,
  `tests/test_recount_e2e.py:178-182`, `tests/test_reconcile_e2e.py`,
  `tests/test_set_chapters_e2e.py`, `tests/test_novel_state_check.py`,
  `tests/test_drafting_bijection_e2e.py`,
  `tests/test_console_scripts_error_arms_e2e.py`,
  `tests/test_console_scripts_e2e.py`, `tests/test_desloppify_e2e.py`,
  `tests/test_wordcount_e2e.py`, `tests/test_novel_done_e2e.py`
- **Severity:** medium

Every installed-binary e2e repeats the same four-line invocation chain to drive
the installed `novel` script:

```python
prog = Program(str(installed_novel_state))
catalogue = single_program_catalogue("novel-state-run", prog)
result = sh.make(prog, catalogue=catalogue)("state", "recount").run_sync(
    context=ExecutionContext(cwd=run_dir), capture=True
)
```

The pattern (`Program(str(...))` -> `single_program_catalogue(...)` ->
`sh.make(...).run_sync(context=ExecutionContext(cwd=...), capture=True)`) recurs
at roughly twenty call sites across twelve modules. `Program(str(installed_novel_state))`
alone appears in six modules; `sh.make(prog, catalogue=catalogue)` appears in
twelve. The 1.2.13 migration widened the duplication: each site now also has to
prepend the mount verb (`"state"`, `"compile"`, …) to its argv tuple by hand.

The BDD step module already factored this out as `_run_installed_argv`
(`tests/steps/per_chapter_loop_installed_steps.py`) — proof the abstraction is
viable — but the standalone e2e modules do not share it. The developers' guide
"Shared test scaffolding" section is explicit that "New shared scaffolding
belongs in `tests/conftest.py` as another fixture rather than a fresh copy in
each module", and the existing audit lineage (`audit-1.2.1.md` .. `audit-1.2.7.md`)
records that this exact duplication class was previously consolidated.

- **Proposed fix:** Add one function-scoped fixture to `tests/conftest.py` (or to
  the registered `installed_binary_fixtures` plugin) exposing a callable such as
  `run_installed_novel(script, *argv, cwd, capture=True) -> result`. It builds the
  `Program`, requests the one-program catalogue, and runs through cuprum with the
  `ExecutionContext(cwd=...)` already wired. Consume it by parameter name in each
  e2e (per the cross-module-import prohibition) so every site collapses to a
  single call. This both removes the boilerplate and centralizes the
  `capture=True` / `ExecutionContext` contract that the migration just touched in
  twelve places.

## Finding 2: `installed_desloppify` re-implements the whole wheel-build/install fixture (medium)

- **Category:** duplication
- **Location:** `tests/test_ai_isms_e2e.py:119-165` (`_build_and_install`,
  `_one_program_catalogue`, `_scripts_dir`, `installed_desloppify`) versus
  `tests/installed_binary_fixtures.py:49-153` (`_one_program_catalogue`,
  `_venv_scripts_dir`, `_run_ok`, `installed_novel_state`)
- **Severity:** medium

`test_ai_isms_e2e.py` carries a private module-scoped fixture `installed_desloppify`
whose `_build_and_install` helper duplicates the entire wheel-build, venv-create,
and install sequence of the shared `installed_novel_state` fixture, down to
copies of `_one_program_catalogue` and a `_scripts_dir` twin of
`_venv_scripts_dir`. Before the migration the two diverged because one resolved
`desloppify` and the other `novel-state`; after 1.2.13 **both resolve the same
`novel` script** (`script_path = scripts_dir / "novel"` in each). The sole
remaining delta is that `installed_desloppify` additionally resolves the installed
`ai-isms.toml` pack and returns a `(script, pack)` tuple. The two fixture
docstrings already cross-reference each other ("exactly as
`test_ai_isms_e2e.py`'s `installed_desloppify` does"), signalling awareness of
the overlap.

Because both fixtures perform a full `uv build --wheel`, the suite now pays for
two slow wheel builds that produce the same artefact and the same installed
`novel` script.

- **Proposed fix:** Have `installed_desloppify` consume the shared
  `installed_novel_state` fixture for the script path and add only the pack
  resolution (`_resolve_installed_pack`) on top, returning
  `(installed_novel_state, pack_path)`. That deletes `_build_and_install`,
  `_one_program_catalogue`, and `_scripts_dir` from `test_ai_isms_e2e.py` and
  removes the redundant second wheel build. If a separate pack-resolving fixture
  is wanted, host it in the `installed_binary_fixtures` plugin beside the
  script fixture so both live with the shared scaffolding the guide mandates.

## Finding 3: Mount-verb derivation is re-rolled in tests instead of reused from production (low)

- **Category:** duplication / inconsistency
- **Location:** `tests/test_console_scripts_e2e.py:69,123`,
  `tests/test_installed_command_names.py:42,45`;
  production source `novel_ralph_skill/commands/novel.py:46-53`
  (`_VERB_FOR_SUBCOMMAND`, `_SUBCOMMAND_FOR_VERB`)
- **Severity:** low

Production already derives the mount verb for each spaced subcommand name once,
from the registry, in `novel.py` (`_VERB_FOR_SUBCOMMAND = {name: name.split(" ",
1)[1] for name in SUBCOMMAND_NAMES}`), and the comment there records the intent
that "the dispatcher never re-spells the verbs inline (Decision Log D4)". The
1.2.13 tests independently re-derive the same verb with `spaced.split(" ", 1)[1]`
and `spaced.partition(" ")`. The derivation is trivial, but it is the kind of
spelling that, if the spaced-name shape ever changed (for example a two-word
verb), would need fixing in both production and several test sites. The
`_VERB_FOR_SUBCOMMAND` map is a private symbol, so the tests cannot reuse it, and
the names registry (`names.py`) — explicitly "the single source of truth" — does
not expose a public verb accessor.

- **Proposed fix:** Promote the verb mapping to `novel_ralph_skill.commands.names`
  as a public, frozen helper (for example `MOUNT_VERBS: tuple[str, ...]` derived
  from `SUBCOMMAND_NAMES`, or `verb_for(spaced) -> str`). Have `novel.py` consume
  it instead of re-deriving `_VERB_FOR_SUBCOMMAND` inline, and have the tests
  import the same accessor rather than re-spelling `split(" ", 1)[1]`. This keeps
  one derivation in the source-of-truth module and lets
  `test_installed_command_names.py` pin the production accessor directly.

## Finding 4: Multiplexer mount names are still hardcoded inline despite the "never re-spell" claim (low)

- **Category:** inconsistency / separation-of-concerns
- **Location:** `novel_ralph_skill/commands/novel.py:84-89` (`build_multiplexer`)
- **Severity:** low

`build_multiplexer` mounts each leaf with a literal verb string:
`app.command(novel_state.build_app(), name="state")`, `name="done"`, and so on.
These five literals re-spell the very verbs `_VERB_FOR_SUBCOMMAND` derives from
`SUBCOMMAND_NAMES` a few lines above, which the D4 comment says the dispatcher
must not do. If a future verb is renamed in the registry, the mount name here will
silently drift from the stamped envelope name, and nothing in the unit tests pins
the mount-name-to-registry correspondence (the e2e catches it, but only via a
slow installed run). This is pre-existing rather than introduced by 1.2.13, but
the migration's reliance on the spaced-name surface makes the drift risk more
material.

- **Proposed fix:** Drive the `name=` arguments from the registry-derived verb
  map (zipping the ordered `build_app` callables against
  `_VERB_FOR_SUBCOMMAND` / the proposed Finding 3 accessor), or add a fast unit
  test asserting that the set of mounted sub-app names equals the set of registry
  mount verbs. The latter is the minimal guard; the former removes the literals
  entirely.

## Finding 5: Users' guide still presents the legacy five scripts as the surface (medium)

- **Category:** docs-gap
- **Location:** `docs/users-guide.md:78-85` ("Installed Commands") and the many
  later `novel-state` / `novel-compile` / `desloppify` / `wordcount` references
  (lines 87-206+)
- **Severity:** medium

The users' guide states that installing a wheel "puts five console-scripts onto
`PATH`" and documents `novel-state`, `novel-done`, `novel-compile`, `desloppify`,
and `wordcount` as the user-facing surface. It contains **zero** references to the
`novel` multiplexer (`grep` for `novel state` / `` `novel` `` returns nothing).
ADR-007 and the 1.2.13 fixture docstrings name the `novel` multiplexer "the
shipping surface", and the installed e2e now drives `novel <sub>` exclusively.
While the legacy five still ship until task 1.2.15, the guide a user reads today
does not mention the command surface the project considers canonical.

The planned task 1.2.14 sweeps "the design prose and diagrams and `SKILL.md`" but
its wording and success criterion name only the design document and `SKILL.md`,
**not** `docs/users-guide.md` or `docs/developers-guide.md`. So this user-facing
sweep is currently untracked.

- **Proposed fix:** Either widen task 1.2.14's scope (and success criterion) to
  include `docs/users-guide.md` and `docs/developers-guide.md`, or add a sibling
  task to rewrite the "Installed Commands" section and every later bare `novel-x`
  reference to the `novel x` form, gated behind 1.2.15 like 1.2.14 so the prose
  flips only once the legacy scripts are actually retired. A proposed roadmap item
  is recorded below; adding it is reserved to the root agent.

## Finding 6: `_LOOP_ARGV` keeps legacy command labels as keys, splitting one concept across two vocabularies (low)

- **Category:** ergonomics / inconsistency
- **Location:** `tests/steps/per_chapter_loop_installed_steps.py:72-79` (`_LOOP_ARGV`)
  and `_run_installed` (passing the literal `"novel"` script name)
- **Severity:** low

The migration kept the `_LOOP_ARGV` dict keyed by the *legacy* operation labels
(`"novel-state"`, `"novel-compile"`, …) while the values became mount-verb argv
(`("state", "recount")`, `("compile", "--check")`). The module docstring and an
inline comment both justify this ("the dict keys stay the legacy operation labels
purely as argv source and capture key … so the `Then`-step capture lookups remain
byte-identical"). The decision is reasonable for a minimal diff, but it leaves the
module straddling two naming vocabularies: a reader now has to hold "the key
`novel-compile` means the `compile` verb" in their head, and `_run_installed`
hardcodes the literal `"novel"` script basename in the call to
`_run_installed_argv`. Once task 1.2.15 removes the legacy names entirely, these
keys become orphaned strings with no remaining referent.

- **Proposed fix:** When the 1.2.15 cleanup lands, re-key `_LOOP_ARGV` on the
  capture labels the `Then` steps actually use (or on the mount verbs) and drop
  the legacy spellings, so the module speaks one vocabulary. Until then, no change
  is required; record the debt so the 1.2.15 implementer re-keys rather than
  leaving dead label strings. Track this against task 1.2.15.

## Summary

The 1.2.13 migration is a clean, well-documented, test-only re-point onto the
`novel` multiplexer, and every touched module carries a migration rationale in its
docstring. The findings are consistency and tidy-up debt: two genuine duplication
clusters in the installed-e2e scaffolding (Findings 1 and 2) that the developers'
guide's own "shared scaffolding in `conftest`" rule would discharge, a small
verb-derivation duplication between production and tests (Findings 3 and 4), a
user-facing documentation lag not covered by the planned 1.2.14 sweep (Finding 5),
and a naming-vocabulary smell best resolved alongside the 1.2.15 cleanup
(Finding 6).
