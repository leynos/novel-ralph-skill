# Post-merge audit — roadmap task 1.2.12

Audit of the codebase after roadmap task 1.2.12 ("Stand up the `novel`
multiplexer dispatcher and entry point") merged to `main` at commit `b17bdd6`.
The slice itself is correct and well-tested: a single `novel` Cyclopts
dispatcher in
[`novel_ralph_skill/commands/novel.py`](../../novel_ralph_skill/commands/novel.py)
mounts the five existing apps additively (per ADR 007, superseding ADR 005), the
command-name registry in
[`novel_ralph_skill/commands/names.py`](../../novel_ralph_skill/commands/names.py)
carries the spaced `novel <verb>` vocabulary without disturbing the legacy
surface, the envelope guard is widened to the transitional superset, and the
dispatch behaviour is pinned both as unit shape
([`tests/test_multiplexer_dispatch.py`](../../tests/test_multiplexer_dispatch.py))
and as in-process legacy-vs-multiplexer envelope equality across every exit arm
([`tests/test_multiplexer_behaviour.py`](../../tests/test_multiplexer_behaviour.py)).
That work needs nothing further on its own terms.

Each finding below records a category, a location, a description, a concrete
proposed fix, and a severity. None is a blocking defect; they are tidy-up
opportunities. Several are *transition states* that the queued roadmap tasks
1.2.13 and 1.2.14 already cover — those are flagged so the root agent does not
double-book them.

Trail followed: explored with `leta`/`grep` and traced history with
`git show --stat`/`sem`. Source of truth consulted:
[`docs/adr-007-command-surface-novel-multiplexer.md`](../adr-007-command-surface-novel-multiplexer.md),
[`docs/adr-003-shared-interface-contract.md`](../adr-003-shared-interface-contract.md),
[`docs/adr-005-command-surface-five-scripts.md`](../adr-005-command-surface-five-scripts.md),
[`docs/developers-guide.md`](../developers-guide.md) §"The `novel` multiplexer",
[`docs/users-guide.md`](../users-guide.md), [`docs/roadmap.md`](../roadmap.md)
(tasks 1.2.12–1.2.14), and [`AGENTS.md`](../../AGENTS.md). Loaded the
`python-router` skill for the Python idiom checks.

## Finding 1 — `novel.main` duplicates the `stub._drive` parse-and-run shape

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`novel_ralph_skill/commands/novel.py:120-136`](../../novel_ralph_skill/commands/novel.py)
  (`main`),
  [`novel_ralph_skill/commands/stub.py:78-107`](../../novel_ralph_skill/commands/stub.py)
  (`_drive`)

`main` and `_drive` share a byte-identical driving body: `parse_global_flags(
sys.argv[1:])`, then `run(app, residual, RunContext(command=…,
working_dir=WORKING_DIR_NAME, human=human))`. `main`'s own docstring concedes it
"generalises the `_drive` shape `stub.py` uses". The only real difference is how
the `command` name is obtained: `_drive` takes a fixed `name`, while `main`
derives it from the residual argv via `_command_name_for`. This is the entry-
point seam ADR 003 §3.1 deliberately keeps single; having two copies of it means
a future change to the pre-parse or `RunContext` stamping must be made in two
places. Roadmap task 1.2.13 removes the five legacy entry points from `stub.py`
but **not** `_drive` itself (the leaf `build_app` callables it drives survive),
so the duplication persists past 1.2.13 unless addressed.

- **Proposed fix:** generalise `_drive` to accept a name *resolver* instead of a
  fixed string — e.g. `name: str | Callable[[list[str]], str]` resolved against
  the residual argv — and have `novel.main` call `_drive(_command_name_for,
  build_multiplexer)`. Alternatively, lift the shared three-line body into a
  small `contract`-level helper (`drive(app, residual, name, *, human,
  working_dir)`) that both call. Sequence after 1.2.13 so the refactor lands on
  the trimmed entry-point set, or note it as the natural home for the 1.2.13
  cleanup.

## Finding 2 — `WORKING_DIR_NAME` is a contract constant living in a command module

- **Category:** separation-of-concerns
- **Severity:** medium
- **Location:**
  [`novel_ralph_skill/commands/novel_state.py:100`](../../novel_ralph_skill/commands/novel_state.py)
  (definition), imported by
  [`novel_ralph_skill/commands/novel.py:36`](../../novel_ralph_skill/commands/novel.py),
  [`novel_ralph_skill/commands/stub.py:23`](../../novel_ralph_skill/commands/stub.py),
  [`novel_ralph_skill/commands/_wordcount.py:44`](../../novel_ralph_skill/commands/_wordcount.py),
  [`novel_ralph_skill/commands/_desloppify.py:48`](../../novel_ralph_skill/commands/_desloppify.py),
  [`tests/multiplexer_support.py:25`](../../tests/multiplexer_support.py)

`WORKING_DIR_NAME = "working"` is a *contract-level* constant: every entry point
stamps it into `RunContext.working_dir`, and the design fixes it as the
invariant working root (Decision Log B4), not a `novel-state` concern. Yet it is
defined in the `novel_state` command module, forcing the multiplexer, the stub
driver, two sibling leaf commands, and the test plugin to import a *peer command
module* purely to reach a shared constant. The 1.2.12 dispatcher adds a fresh
such import (`novel.py:36`). The constant belongs beside `RunContext` in the
`contract` package, where the working-directory field it feeds already lives.

- **Proposed fix:** move `WORKING_DIR_NAME` (and the `working_root()` accessor at
  `novel_state.py:106-111`, if it generalises cleanly) into
  [`novel_ralph_skill/contract/runner.py`](../../novel_ralph_skill/contract/runner.py)
  beside `RunContext`, re-export it from `novel_ralph_skill.contract`, and update
  the six import sites. Leave a thin re-export in `novel_state` only if a gate
  pins the old path. This removes the command-to-command coupling and gives the
  multiplexer a contract-package import for a contract constant.

## Finding 3 — `contract.envelope` imports from `commands`, inverting the layering

- **Category:** separation-of-concerns
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/contract/envelope.py:19`](../../novel_ralph_skill/contract/envelope.py)
  (`from novel_ralph_skill.commands.names import ENVELOPE_COMMAND_NAMES`)

The `contract` package is the lower, shared layer: fourteen `commands` modules
import from it. The sole reverse edge is `envelope.py`'s import of
`ENVELOPE_COMMAND_NAMES` from `commands.names`, which 1.2.12 re-pointed (from
`COMMAND_NAMES` to the wider superset). A lower layer reaching up into the
command package to validate its own `command` field is a layering inversion: the
envelope guard's universe of valid names is owned above it. It is pre-existing
but the 1.2.12 re-point reinforces it, and the same edge will need re-pointing
again at 1.2.13 when the legacy names are dropped.

- **Proposed fix:** relocate the *command-name vocabulary* (the legacy tuple, the
  spaced subcommand tuple, the multiplexer name, and `ENVELOPE_COMMAND_NAMES`)
  into the `contract` package (e.g. `contract/command_names.py`), and have
  `commands.names` import the vocabulary from there while keeping the
  `[project.scripts]`-binding concerns (`COMMAND_ENTRY_POINTS`,
  `project_scripts_table`) in `commands`. That restores a clean
  `commands → contract` dependency direction and gives 1.2.13 a single contract-
  package edit for the name drop. If the layering is intentionally tolerated,
  record the rationale in ADR 003 so the reverse edge is documented rather than
  incidental.

## Finding 4 — no installed-binary e2e exercises the `novel` console script

- **Category:** test-gap
- **Severity:** low
- **Location:**
  [`tests/test_console_scripts_e2e.py:56-64`](../../tests/test_console_scripts_e2e.py)
  (`_REAL_COMMANDS` / `COMMAND_NAMES`),
  [`pyproject.toml`](../../pyproject.toml) `[project.scripts]`

As of 1.2.12 `novel` is a registered `[project.scripts]` entry point bound to
`novel_ralph_skill.commands.novel:main`, yet the installed-binary e2e suite
drives only `COMMAND_NAMES` (the legacy five). The multiplexer is verified at the
pyproject-table level
([`tests/test_pyproject_scripts.py`](../../tests/test_pyproject_scripts.py)) and
in-process (via the `driver` fixture), but nothing installs the wheel and runs
the real `novel` binary as a subprocess. So the one entry point the design will
keep is the only one with no end-to-end install-and-run proof. Roadmap task
1.2.13 migrates the installed-binary e2e to `novel <sub>`, so this is a known
transition state — but until then the new entry point has the weakest e2e
coverage of the surface.

- **Proposed fix:** covered by roadmap task 1.2.13 (migrate the installed-binary
  e2e to invoke `novel <sub>`). No new work to schedule; recorded so the gap is
  not mistaken for an oversight. If 1.2.13 slips, consider an interim
  install-and-run smoke for `novel state check` so the bound entry point is not
  left untested end-to-end.

## Finding 5 — the users-guide does not mention the `novel` multiplexer surface

- **Category:** docs-gap
- **Severity:** low
- **Location:** [`docs/users-guide.md`](../users-guide.md) (no `novel state` /
  `novel done` / `novel compile` / `novel desloppify` / `novel wordcount`
  references), contrast with
  [`docs/developers-guide.md`](../developers-guide.md) §"The `novel`
  multiplexer" (lines 322+), which documents it well

The developers-guide gained a clear multiplexer section in 1.2.12, but the
users-guide still presents the command surface in terms of the legacy five.
Roadmap task 1.2.14 ("Sweep the design and skill prose to the `novel`
multiplexer") explicitly covers the prose sweep, so this is a tracked transition
state rather than a fresh omission. The risk is only that a user reading the
users-guide today would not learn the `novel <verb>` invocation that
`[project.scripts]` now installs.

- **Proposed fix:** covered by roadmap task 1.2.14. When that task runs, ensure
  the users-guide invocation examples are swept alongside the design and skill
  prose (the task currently names "design prose and diagrams and `SKILL.md`" —
  confirm the users-guide is in its scope, and widen it if not).

## Finding 6 — `_command_name_for` keys on "first non-flag token", an implicit assumption

- **Category:** ergonomics
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/commands/novel.py:114`](../../novel_ralph_skill/commands/novel.py)
  (`verb = next((token for token in residual if not token.startswith("-")),
  None)`)

`_command_name_for` selects the command verb as the first token in the residual
argv that does not start with `-`. This is correct for the present surface
because `parse_global_flags` has already removed the only global flag
(`--human`), so the leading positional is the verb. But the rule is an implicit
contract: if a future global flag took a *value* (e.g. `--profile fast state
check`), the value `fast` would be the first non-flag token and the verb
resolution would silently mis-key, falling back to the bare `"novel"` name and
mis-stamping the envelope. The behaviour is unit-tested for today's argv shapes
([`test_command_name_for_maps_residual_argv`](../../tests/test_multiplexer_dispatch.py)),
but the assumption ("all options are valueless booleans stripped before this
point") is undocumented at the call site.

- **Proposed fix:** add a one-line `why:` comment at `novel.py:114` recording the
  assumption that the residual argv carries no option-with-value before the verb
  (because `parse_global_flags` strips the sole boolean global flag), so a future
  valued global flag is flagged as needing this resolver revisited. No behaviour
  change; this is a tripwire against a latent footgun, consistent with the
  codebase's heavy `why:`-comment discipline.
