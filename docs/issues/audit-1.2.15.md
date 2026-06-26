# Post-merge audit — roadmap task 1.2.15

Task 1.2.15 retired the legacy console-script surface: it reduced
`[project.scripts]` to the single `novel` multiplexer, deleted
`novel_ralph_skill/commands/stub.py`, dropped the `STUB_MODULE`,
`COMMAND_ENTRY_POINTS`, and `COMMAND_NAMES` registry symbols, swept the suite's
command-name stamps to the spaced `novel <verb>` form, and added
`tests/test_legacy_surface_retired.py` as the durable regression guard.

This audit reviews the merged state at `origin/main` (commit `9e95c49`) for
refactoring opportunities, duplication, inconsistencies, separation-of-concerns
and CQS issues, and gaps in documentation and tests. Each finding records a
location and a concrete proposed fix.

The legacy-script references still present in `docs/users-guide.md`,
`docs/developers-guide.md`, `docs/novel-ralph-harness-design.md`, and
`skill/novel-ralph/SKILL.md` are **out of scope**: they are explicitly tracked by
roadmap tasks 1.2.14 and 1.2.16, which are gated behind 1.2.15 and not yet done.
They are noted here only to confirm they remain tracked, not as new findings.

## 1. Verb-extraction idiom `name.split(" ", 1)[1]` replicated across three sites

- **Category:** duplication
- **Severity:** medium
- **Location:** `novel_ralph_skill/commands/novel.py:47`;
  `tests/test_console_scripts_e2e.py:69`; `tests/test_console_scripts_e2e.py:123`

The mapping from a spaced subcommand name (`"novel state"`) to its bare mount
verb (`"state"`) is open-coded as `name.split(" ", 1)[1]` in three independent
places: the dispatcher's `_VERB_FOR_SUBCOMMAND` comprehension and twice in the
console-scripts e2e module. The registry module
(`novel_ralph_skill/commands/names.py`) is documented as the single source of
truth for the command-name vocabulary, yet the spaced-name-to-verb derivation —
a true piece of that vocabulary — lives outside it and is re-spelled by every
consumer.

This is the same duplication the prior audit `audit:1.2.13` flagged (proposing a
`verb_for(spaced) -> str` or `SUBCOMMAND_VERBS` accessor in `names.py`). Task
1.2.15 touched both `novel.py` and the e2e suite and reproduced the idiom rather
than consolidating it; no remediation roadmap item was ever opened, so the debt
has now persisted across two tasks.

- **Proposed fix:** add a public derivation to
  `novel_ralph_skill/commands/names.py` — either `SUBCOMMAND_VERBS: tuple[str, ...]`
  (the verbs in surface order) or `verb_for(spaced: str) -> str`. Have `novel.py`
  build `_VERB_FOR_SUBCOMMAND` from it and have `test_console_scripts_e2e.py`
  import it instead of re-spelling `split(" ", 1)[1]`. One derivation, owned by
  the source-of-truth module.

## 2. `per_chapter_loop_steps` capture keys mix bare verbs and spaced names

- **Category:** inconsistency
- **Severity:** low
- **Location:** `tests/steps/per_chapter_loop_steps.py:142,156` (`"recount"`),
  `:317,325` (`"advance-phase"`) versus `:166,183,211,229` (`"novel done"`,
  `"novel wordcount"`, `"novel desloppify"`, `"novel compile"`)

The `_Outcome.captures` dict is keyed inconsistently. Four of the six captures
use the spaced command name (`"novel done"`, `"novel wordcount"`,
`"novel desloppify"`, `"novel compile"`) — which doubles as the `command_name`
argument passed to `_run_capturing` and stamped into the `RunContext`. But two
captures use a bare verb that is *not* a command name: `"recount"` and
`"advance-phase"` are stored under their argv sub-verb while their
`command_name` is `"novel state"`. A reader cannot tell from the key alone
whether it denotes a command name or an argv token, and `_result(outcome, ...)`
is called with both flavours.

- **Proposed fix:** key every capture by a single consistent scheme. The
  cleanest is the operation label the scenario actually distinguishes by (the
  argv sub-verb where one exists: `recount`, `advance-phase`, `done`, `wordcount`,
  `desloppify`, `compile`), so each `Then` reads back the same logical step it
  ran. Alternatively, key all six by the spaced `command_name` and disambiguate
  the two `novel state` captures with a small composite key. Either way, remove
  the bare-verb/spaced-name split.

## 3. `novel.py` docstrings reference the deleted `stub.py` in the present tense

- **Category:** docs-gap
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/novel.py:64,74,139`

Task 1.2.15 deleted `novel_ralph_skill/commands/stub.py`, but three docstrings
and comments in `novel.py` still describe it as a live module: "the per-command
import laziness `stub.py` already relies on" (line 64), "mirror `stub.py`'s
per-command laziness" (line 74), and "Generalises the `_drive` shape `stub.py`
uses" (line 139). These read as present-tense references to code that no longer
exists, so a maintainer following the citation will look for a module that was
removed in the same task that wrote (and now keeps) these lines.

- **Proposed fix:** rephrase to past tense and drop the dangling module
  pointer — e.g. "preserves the per-command import laziness the retired
  per-script entry points relied on" — or state the rationale directly
  (deferring the five leaf imports until the multiplexer is built) without
  naming the deleted module.

## 4. `test_contract_app_centralisation` labels build-apps with retired hyphenated names

- **Category:** inconsistency
- **Severity:** low
- **Location:** `tests/test_contract_app_centralisation.py:3,58-61`

The `_real_build_apps` helper returns `(name, build_app)` tuples whose name
slots are the *legacy hyphenated* console-script names — `"novel-state"`,
`"novel-done"`, `"novel-compile"`, `"desloppify"` — and the module docstring
opens by naming the constructors `novel-state`, etc. After 1.2.15 those
hyphenated literals no longer name anything the package ships; every other
swept module now labels these constructors by their spaced surface
(`"novel state"`) or bare mount verb (`"state"`). These labels are descriptive
only (they are not asserted against the registry), so the test still passes, but
they are stale and inconsistent with the post-1.2.15 vocabulary, and they are not
caught by `test_legacy_surface_retired.py` (that module is not in its
`_IDIOM_SOURCES` scan list).

- **Proposed fix:** relabel the four tuples and the docstring to the spaced
  surface (`"novel state"` …) or the bare mount verbs (`"state"`, `"done"`,
  `"compile"`, `"desloppify"`), matching the convention the rest of the swept
  suite now uses. Consider adding this module to the durable guard's idiom-source
  scan so a re-introduced hyphenated label is caught.

## 5. `names.py` module docstring cites sources retired by 1.2.15 without dating them

- **Category:** docs-gap
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/names.py:1-8`

The opening paragraph still describes the registry as collapsing the name lists
"in `stub.py`, `pyproject.toml`, and three test modules" onto one registry. The
`stub.py` and "three test modules" framing is historical (task 1.2.4) and the
docstring does later note 1.2.15 retired the legacy surface, so this is softer
than finding 3 — but a fresh reader meets a present-tense list of consumers, two
of which (`stub.py`; the legacy-name test modules) no longer exist, before the
sentence that retires them. The history is worth keeping; the framing should make
clear it is history.

- **Proposed fix:** reword the lead so the retired consumers are unambiguously
  past — e.g. "task 1.2.4 collapsed the previously duplicated name lists (then in
  `stub.py`, `pyproject.toml`, and three test modules); task 1.2.15 retired the
  legacy surface, so the registry now describes exactly the single `novel`
  multiplexer." Keeps the provenance, removes the false present tense.

## 6. No behavioural coverage that the durable guard's source-scan lists stay complete

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/test_legacy_surface_retired.py:43-60`
  (`_IDIOM_SOURCES`, `_REPOINTED_E2E`)

`test_legacy_surface_retired.py` is the lasting regression guard, but two of its
checks scan only a *hand-maintained* list of file paths (`_IDIOM_SOURCES`,
`_REPOINTED_E2E`). A legacy command stamp re-introduced in any file *not* on
those lists — a new e2e module, say — would slip past the guard silently. The
guard's own docstring acknowledges these are enumerations of the files 1.2.15
touched, but nothing pins the lists to reality, so they will quietly rot as the
suite grows. (Finding 4 is a live instance: a stale hyphenated label sits in a
module outside `_IDIOM_SOURCES`.)

- **Proposed fix:** add a test that asserts every `_IDIOM_SOURCES` and
  `_REPOINTED_E2E` path still exists on disk (so a renamed/deleted file fails
  loudly rather than silently dropping coverage). For stronger protection,
  broaden the hyphenated-literal scan to walk `tests/` and
  `novel_ralph_skill/` wholesale (excluding this guard module and the
  feature-file-bound step decorators), turning the curated list into a
  belt-and-braces fast path rather than the sole coverage.
