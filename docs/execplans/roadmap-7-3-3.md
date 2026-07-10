# Consolidate the draft-read state-error wrapper shared by wordcount, recount, and desloppify

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & discoveries`, `Decision log`,
and `Outcomes & retrospective` must be kept up to date as work proceeds.

Status: DRAFT (round 1)

Note: this file previously held the ExecPlan for the "direct-edit guard" task,
which the roadmap renumbered to 7.6.3 and merged at commit `b28eaad` (recoverable
from git history). The current roadmap task 7.3.3 is the draft-read wrapper
consolidation this plan covers.

## Purpose / big picture

Three command modules in `novel_ralph_skill/commands/` open-code the same
"draft-read fault guard": run a disk reader, catch the shared
`STATE_INPUT_ERRORS` tuple, and re-raise the caught exception as the actionable
exit-`3` `StateInputError` that `state_sourcing._draft_read_error` builds, so an
undecodable or unreadable chapter `draft.md` reaches exit `3` (the "stop and
recover state" channel, design §3.2) rather than escaping to the benign exit `1`
("keep looping", design §3.2). The three sites are:

- `_wordcount._recount_or_state_error`
  (`novel_ralph_skill/commands/_wordcount.py` lines 62-103);
- `_recount._recount_or_state_error`
  (`novel_ralph_skill/commands/_recount.py` lines 58-97); and
- `_desloppify.source_chapters`'s `try/except` tail
  (`novel_ralph_skill/commands/_desloppify.py` lines 202-211).

Each is the identical control-flow shell — `try: <read>; except
STATE_INPUT_ERRORS as exc: raise _draft_read_error(<working_dir>) from exc` —
differing only in the read body it wraps (a `recount_words(...)` call in two
sites, a `ScannedChapter(...)` comprehension in the third) and in what it
returns. Every one of their docstrings explicitly says it "mirrors" the others,
which is the drift this task removes. The audit that flagged it
(`docs/issues/audit-6.1.1.md` Finding 1) records the triplication and proposes
"a single `read_drafts_or_state_error(...)` helper (or a thin
`state_error_on(...)` context manager) into a shared module … and have all three
call sites delegate to it".

After this change, the one fault-routing rule — *which* read faults become exit
`3`, and *how* they are re-raised — lives in exactly one place in
`state_sourcing`, the neutral state-sourcing home that task 7.3.1 carved out, and
the three commands delegate to it instead of each re-spelling the `try/except`
shell. The observable behaviour of all three commands is byte-for-byte
unchanged: the same exit `3`, the same actionable message, the same envelope.
This is verified by the existing cross-boundary parity test
(`tests/test_draft_read_message_parity.py`) staying green, plus a new structural
anti-drift test that pins the single-home property so the guard cannot silently
re-fork.

## Why a context manager, not a `read_drafts_or_state_error(working_dir, manifest)` function

The audit offered two shapes. The plan picks the context manager
(`state_error_on`/`draft_read_guard`) and rejects the
`read_drafts_or_state_error(working_dir, manifest)` reader-function shape,
because the three read bodies are *not* the same call:

- `_wordcount` and `_recount` both call
  `recount_words(working_dir, manifest) -> tuple[int, Mapping[str, int]]`
  (`novel_ralph_skill/state/wordcount.py` line 86), but `_wordcount` discards the
  total and returns only `by_chapter` while `_recount` returns the full
  `(current, by_chapter)` tuple; and
- `_desloppify.source_chapters` wraps a `tuple(ScannedChapter(number=…,
  text=_chapter_text(working_dir, entry.number)) for entry in selected)`
  comprehension over `_chapter_text` (`_desloppify.py` lines 82-122, 202-211) —
  a different reader entirely.

A `read_drafts_or_state_error` helper would therefore have to fix one reader
(`recount_words`) and one return shape, which serves at most two of the three
sites and cannot serve the `desloppify` comprehension at all. The shared part is
exactly the *guard* (the `try/except STATE_INPUT_ERRORS → _draft_read_error`
shell), and a context manager is the precise abstraction for "wrap an arbitrary
block in a fixed exception-translation policy"
(`.rules/python-context-managers.md`: "Reduces boilerplate and visually scopes
side effects"; AGENTS.md "Use functions and composition … extract reusable
logic"). This is the same reasoning the audit flagged as the second, preferred
option. The decision is recorded in the Decision log (D1) and is **not** a fork
left for the implementer.

## Scope: three named sites now; the three adjacent sites are a separate, recorded follow-on

`state_sourcing._draft_read_error` is consumed by **six** draft-read boundaries
today (its own docstring and `tests/test_draft_read_message_parity.py` enumerate
them): the three this task names plus `_novel_done` (`_novel_done.py` lines
92-96) and `_compile`'s two tails (`_compile.py` lines 138-144 and 217-223). All
six open-code the same guard shell. The roadmap scopes task 7.3.3 to the three
named commands (`wordcount`, `recount`, `desloppify`); the success criterion
names exactly those three. To keep this slice atomic and its blast radius bounded
(AGENTS.md "small, focused, atomic changes"), this plan migrates the three named
sites only, and the new context manager is written so the remaining three sites
can adopt it later with no signature change. Migrating the other three is recorded
as Decision D2 and Risk R3, not silently bundled in; doing so here would widen the
diff past the success criterion's named surface. If the implementer judges the
same-named-shell migration of the other three trivial and in-scope, that is an
escalation point (see Tolerances), not an improvisation.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- The new context manager must live in
  `novel_ralph_skill/commands/state_sourcing.py`, the neutral state-sourcing home
  (roadmap 7.3.1; developers-guide "The exit-3 messages are actionable"
  paragraph). It must **not** be re-pinned to
  `novel_ralph_skill/commands/novel_state.py` (the command facade): the roadmap
  task explicitly says "Coordinate with 7.3.1 so the wrapper lands in the neutral
  state-sourcing home rather than re-pinning it to `novel_state`".
- `state_sourcing.py` must keep its no-`novel_state`-import rule: it imports only
  from `novel_ralph_skill.state` and `novel_ralph_skill.contract.runner` (module
  docstring lines 14-21). The context manager adds only a
  `contextlib`/`collections.abc` standard-library import and reuses the
  module-local `_draft_read_error` and `STATE_INPUT_ERRORS`; it introduces no new
  cross-module dependency and no import cycle.
- The exit-`3` fault-routing behaviour of all three commands is unchanged:
  - an absent `draft.md` is still the one benign read fault absorbed inside
    `recount_words`/`_chapter_text` (returns `0`/`""`), never reaching the guard
    (design §5.4; `recount_words` docstring lines 103-105);
  - every other read fault (`UnicodeDecodeError`, `PermissionError`,
    `IsADirectoryError`, any other non-`FileNotFoundError` `OSError`) is still
    re-raised as `StateInputError` and reaches exit `3`, never exit `1`
    (design §3.2);
  - the caught exception is still chained via `raise … from exc` so the
    `messages` channel carries only actionable prose, no `Errno`/`{exc}`/traceback
    (developers-guide "leaks no raw `Errno`"; `_draft_read_error` docstring);
  - the actionable message is still exactly the one `_draft_read_error`
    interpolates from the reported `working/` directory.
- `state_sourcing.py` and every command module stays under the 400-line file cap
  (AGENTS.md "Keep file size manageable"). `state_sourcing.py` is 383 lines today;
  the context manager adds roughly 30-45 lines of body plus docstring, so the
  implementer must confirm the file stays ≤ 400 (Tolerance below) and, if it would
  exceed, escalate rather than split mid-task.
- `make all` (which runs `build check-fmt lint typecheck test`) passes before the
  commit. `make all` includes 100% docstring coverage via `interrogate` and
  Pylint, so the new context manager needs a full numpydoc-style docstring with
  a usage example (AGENTS.md "Function documentation must include clear
  examples").
- en-GB Oxford spelling ("-ize"/"-yse"/"-our") in all prose, docstrings,
  comments, and the commit message (standing rules; AGENTS.md "consistent
  spelling").

## Tolerances (exception triggers)

- Scope: this is a tightly bounded refactor. If implementation touches more than
  6 files (`state_sourcing.py`, the three command modules, the new test file(s),
  and the developers' guide) or more than ~250 net lines, stop and escalate.
- Interface: the three command modules keep their public function signatures
  (`source_state_and_drafts`, `recount`, `source_chapters`) and their private
  helper signatures unless a helper becomes a trivial one-liner that the guard
  inlines (see Plan of work WI3). If a *public* signature must change, stop and
  escalate.
- File cap: if adding the context manager pushes `state_sourcing.py` past 400
  lines, stop and escalate (do not split the module mid-task).
- Behaviour: if any existing test in `tests/test_draft_read_message_parity.py`,
  `tests/test_wordcount_command.py`, `tests/test_recount_unit.py`,
  `tests/test_recount_bdd.py`, `tests/test_desloppify_sourcing.py`,
  `tests/test_desloppify_command.py`, or any e2e suite changes its expected
  output, stop and escalate — observable behaviour must not move.
- Iterations: if `make all` still fails after 3 focused fix attempts on a work
  item, stop and escalate.
- Adjacent sites: if the implementer concludes the three out-of-scope sites
  (`_novel_done`, `_compile` ×2) should migrate in this slice, stop and escalate
  (the roadmap success criterion names only the three; see Decision D2).

## Risks

```plaintext
    - Risk: R1 — the context manager swallows an exception it should not, or fails
      to re-chain, changing the message or the exit code.
      Severity: high
      Likelihood: low
      Mitigation: the `except STATE_INPUT_ERRORS` clause and the
      `raise _draft_read_error(reported_dir) from exc` re-raise are copied verbatim
      from the existing sites; the cross-boundary parity test
      (`tests/test_draft_read_message_parity.py`) and the per-command exit-3 tests
      pin the message and code and must stay green unchanged.

    - Risk: R2 — a `with` block that wraps too much (e.g. wrapping
      `load_or_state_error` or the manifest selection inside the guard)
      accidentally re-routes a *non*-draft fault — a missing `state.toml` or a bad
      `--chapter` — through the draft-read formatter.
      Severity: medium
      Likelihood: low
      Mitigation: the guard wraps only the draft-read body, exactly the span the
      current `try` covers. `source_chapters` keeps `load_or_state_error` and
      `_select_chapters` (the exit-3 state-load and exit-2 usage faults) *outside*
      the `with`. The new structural test asserts the migrated handlers are gone,
      and `tests/test_desloppify_sourcing.py` / `tests/test_wordcount_command.py`
      pin the bad-`state.toml` and bad-`--chapter` routes unchanged.

    - Risk: R3 — scope creep into the three adjacent draft-read sites or into the
      `disk_evidence` reader (which lives in the `state` package, below the command
      layer, and cannot import `state_sourcing`).
      Severity: low
      Likelihood: medium
      Mitigation: Decision D2 fixes the scope at the three named commands;
      `disk_evidence` is explicitly out of scope (it is below the command layer and
      routes through `_novel_done`/`_compile`, not directly). The Tolerances make
      adjacent-site migration an escalation point.

    - Risk: R4 — `state_sourcing.py` crosses the 400-line cap.
      Severity: low
      Likelihood: low
      Mitigation: the file is 383 lines; measure after the edit (Tolerance). The
      context manager is small. If it would cross, escalate rather than split.
```

## Progress

- [x] WI1. Add the `draft_read_guard` context manager to `state_sourcing.py`
  with a full docstring and unit tests (red before, green after). Done at commit
  pending; `make all` green; `state_sourcing.py` trimmed to exactly 400 lines
  (see Decision D5). coderabbit: 1 minor finding (bare asserts in the new unit
  test) addressed.
- [x] WI2. Route `_recount._recount_or_state_error` through the guard. Resolves
  `_working_dir()` once (Decision D4); drops the now-unused `STATE_INPUT_ERRORS`
  / `_draft_read_error` imports. Extended `test_recount_undecodable_draft_refuses`
  to assert the refusal carries the shared "cannot read the drafts under" message,
  proving the guard is wired. `make all` green. coderabbit: 0 findings on the WI2
  code; the 5 reported findings all target pre-existing untracked planning review
  notes (`*.review-round-*.md`, `*.logisphere-review-r1.md`), out of scope for
  this code work item (left untouched).
- [x] WI3. Route `_wordcount._recount_or_state_error` through the guard. Wraps
  only the `recount_words` reader; the `return by_chapter` stays outside the
  `with`. Drops the now-unused `STATE_INPUT_ERRORS` / `_draft_read_error` imports
  (kept `WORKING_DIR_NAME`, `load_or_state_error`). The existing
  `tests/test_wordcount_command.py` exit-3 cases stay green unchanged. `make all`
  green. coderabbit: 0 findings on the WI3 code; its single finding targets a
  pre-existing untracked planning review note, out of scope (left untouched).
- [x] WI4. Route `_desloppify.source_chapters` through the guard. Only the
  `tuple(...)` comprehension is wrapped; `load_or_state_error` and
  `_select_chapters` stay outside the `with` (Risk R2 preserved). `tuple(...)`
  forces the draft reads eagerly inside the guard. Dropped the now-unused
  `STATE_INPUT_ERRORS` / `_draft_read_error` imports (kept `_rule_pack_read_error`,
  still used by `_desloppify`). The existing `tests/test_desloppify_sourcing.py`
  already pins the corrupt-draft "cannot read the drafts under" message (exit 3),
  the bad-`--chapter` exit-2 split, and the missing-`state.toml` load fault, all
  green unchanged — no new test needed. `make all` green.
- [x] WI5. Add the structural single-home anti-drift test
  (`tests/test_draft_read_guard_home.py`). Walks each of the three migrated
  modules with `ast`: asserts each imports `draft_read_guard` from
  `state_sourcing`, and that no `except STATE_INPUT_ERRORS` handler re-raising
  `_draft_read_error(...)` remains. The two out-of-scope modules
  (`_novel_done`, `_compile`) are excluded by name (Decision D2). Verified the
  detector is load-bearing: it flags the still-open-coded shells in
  `_novel_done.py` / `_compile.py` and finds the three migrated modules clean.
  Helper predicates were factored out to stay under the 2-boolean-expression
  pylint limit. `make all` green (1491 passed).
- [x] WI6. Update the developers' guide and validate the markdown. Added a
  sibling paragraph after the `_draft_read_error` prose recording that the
  guard shell is now homed in `draft_read_guard`, that `wordcount`/`recount`/
  `desloppify` delegate to it via `with draft_read_guard(...)`, that a structural
  test pins the single home, and that the three other boundaries (`novel done`,
  both `novel compile` tails) still open-code the shell pending a later slice.
  Added `draft_read_guard` to the seam listing. `make markdownlint`, `make nixie`,
  and `make all` green.

## Surprises & discoveries

```plaintext
    - Observation: the message string the audit flagged as identical across
      `_wordcount`/`_desloppify` (`f"cannot read chapter drafts: {exc}"`) no longer
      exists in the tree.
      Evidence: roadmap task 6.3.5 (post-6.1.1) already routed all six draft-read
      boundaries through the shared `_draft_read_error` formatter; the three sites
      now call `raise _draft_read_error(working_dir) from exc`, not an inline
      f-string. Verified by reading `_wordcount.py:102`, `_recount.py:97`,
      `_desloppify.py:211`.
      Impact: the *message* is already single-homed; the residual duplication is
      purely the `try/except` *guard shell*. The consolidation target is the
      control flow, not the message string. The plan is scoped accordingly.

    - Observation: the same guard shell appears in three further sites
      (`_novel_done`, `_compile` ×2) that the roadmap does not name in 7.3.3.
      Evidence: `tests/test_draft_read_message_parity.py` enumerates all six
      boundaries; grep over `except STATE_INPUT_ERRORS` confirms six occurrences
      routing to `_draft_read_error`.
      Impact: the context manager is written to serve all six, but only the three
      named sites migrate in this slice (Decision D2).
```

## Decision log

```plaintext
    - Decision: D1 — consolidate via a `contextlib.contextmanager` named
      `draft_read_guard(reported_dir: pathlib.Path)`, not a
      `read_drafts_or_state_error(working_dir, manifest)` reader function.
      Rationale: the three read bodies differ (two `recount_words` calls with
      different return shapes; one `ScannedChapter` comprehension over
      `_chapter_text`), so a fixed-reader helper cannot serve all three. The shared
      part is the exception-translation guard, which a context manager expresses
      exactly (`.rules/python-context-managers.md`; AGENTS.md composition
      guidance). This was the audit's preferred second option.
      Date/Author: 2026-06-27, planning agent.

    - Decision: D2 — migrate only the three roadmap-named sites (`_wordcount`,
      `_recount`, `_desloppify`); leave `_novel_done` and `_compile`'s two tails on
      their open-coded shells for a later slice.
      Rationale: the roadmap success criterion names exactly the three; keeping the
      diff to the named surface preserves atomicity (AGENTS.md). The context
      manager is written so the other three adopt it later with no signature
      change.
      Date/Author: 2026-06-27, planning agent.

    - Decision: D3 — the guard takes the already-resolved reported directory
      (`reported_dir: pathlib.Path`), not the manifest or the reader, mirroring
      `_draft_read_error(reported_dir)`'s own single parameter. The caller resolves
      `working_dir` (via `state_sourcing.working_dir()` /
      `_state_mutators._working_dir()` / the local
      `pathlib.Path(WORKING_DIR_NAME)`) and passes it in. This keeps the guard free
      of any reader or manifest coupling and identical for all six sites.
      Rationale: the reported directory is the only datum `_draft_read_error`
      consumes; threading the reader through the manager would re-introduce the
      reader-shape divergence D1 avoids.
      Date/Author: 2026-06-27, planning agent.

    - Decision: D5 — the file-cap Tolerance fired as predicted, but escalation
      resolved to "keep the guard in `state_sourcing` (hard Constraint + the
      Interfaces contract pin it there) and reclaim the few lines its docstring
      cost from genuinely redundant prose elsewhere in the same module", not to
      split the module or relocate the guard. The plan's arithmetic was optimistic:
      the module was 382 lines and a numpydoc-complete public function pushed it to
      441, so it could never fit under 400 by addition alone. The `too-many-lines`
      pylint check IS gate-enforced (the pypy shim re-enables it even though the
      stock-pylint config disables it), so 400 is a hard gate, not a guideline.
      Resolution: the new guard carries a full numpydoc docstring (summary, scope
      paragraph, Parameters/Yields/Raises/Examples); the reclaimed lines came from
      collapsing the four sibling file-fault formatters' duplicated "renders from
      the path alone; the caller keeps the caught exception solely for `raise …
      from exc` chaining — no `Errno`/`{exc}`/traceback" boilerplate (which
      `_file_fault_error` already documents as the shared contract) and trimming
      decision-citation line-number noise. No code logic, message string, or test
      expectation changed; only redundant docstring/comment prose. `state_sourcing.py`
      now sits at exactly 400 lines. This is the only deviation; it is
      behaviour-neutral and recorded here per the Tolerances escalation rule.
      Date/Author: 2026-06-27, implementing agent.

    - Decision: D4 — `_recount`'s wrapper currently calls `_working_dir()` twice
      (once in the `try` body, once in the `except`). When it adopts the guard it
      resolves `_working_dir()` once into a local and passes that local both to the
      reader and to `draft_read_guard`, removing the double resolution.
      Rationale: a single resolution is clearer and provably identical (the
      function is pure). This is the only incidental behaviour-preserving cleanup;
      it changes no output.
      Date/Author: 2026-06-27, planning agent.
```

## Outcomes & retrospective

Completed. The guard is single-homed as `state_sourcing.draft_read_guard` (in
`__all__`); `_wordcount`, `_recount`, and `_desloppify` each delegate to it via
`with draft_read_guard(working_dir): …` and no longer open-code the
`try/except STATE_INPUT_ERRORS → _draft_read_error` shell. The cross-boundary
parity test (`tests/test_draft_read_message_parity.py`) and every named
per-command suite stayed green with no edit, confirming behaviour did not move;
two per-command exit-3 tests were *extended* (not changed) to assert the shared
draft-read message, proving each guard is wired. The structural anti-drift suite
(`tests/test_draft_read_guard_home.py`) pins import, `with`-usage, and the
absence of the open-coded shell across the three migrated modules, and is
verified load-bearing (it flags the still-open-coded `_novel_done`/`_compile`
shells). The developers' guide records the consolidation.

Deviations: only Decision D5 (the file-cap Tolerance fired; resolved by trimming
redundant docstring/comment prose to land `state_sourcing.py` at exactly 400
lines, the hard gate). Adjacent-site migration (`_novel_done`, `_compile` ×2)
was correctly left out of scope (Decision D2; Risk R3). No public signature
changed. coderabbit raised one actionable (major) finding on the WI5 structural
test — that import + absence alone do not prove *use* — which was addressed by
adding the `with draft_read_guard(...)` usage assertion; all other coderabbit
findings targeted pre-existing untracked planning review notes outwith this
task's scope.

## Context and orientation

The codebase is a Python package, `novel_ralph_skill`, that ships a `novel`
command-line multiplexer for running a long-form-fiction harness. Commands live
under `novel_ralph_skill/commands/`. The relevant ones are read-only checkers and
mutators that read chapter drafts from a fixed `working/` directory tree
(`working/manuscript/chapter-NN/draft.md`) and a typed `working/state.toml`.

The contract (design §3.2, `docs/novel-ralph-harness-design.md` lines 212-242)
fixes five exit codes. Exit `3` ("state or input error") tells the harness to
stop and recover; exit `1` ("benign negative") tells it to keep looping. A draft
file that exists but is unreadable or undecodable must reach exit `3`, never
exit `1` — otherwise the harness loops forever on a corrupt manuscript. A
command signals exit `3` by raising
`novel_ralph_skill.contract.runner.StateInputError`, which the shared `run`
wrapper maps to the exit-`3` envelope.

`novel_ralph_skill/commands/state_sourcing.py` is the "neutral state-sourcing
home" carved out by roadmap task 7.3.1. It owns *where* a command looks
(`WORKING_DIR_NAME`, `working_dir()`, `state_path()`), *what counts* as a
state-input fault (`STATE_INPUT_ERRORS`, a tuple of `OSError`,
`tomllib.TOMLDecodeError`, `KeyError`, `ValueError`, `TypeError`), and *how* a
failed load or read becomes the actionable exit-`3` error (the sibling formatters
`_state_input_error`, `_draft_read_error`, `_compile_write_error`,
`_rule_pack_read_error`, `_device_ledger_read_error`, plus the public
`load_or_state_error`). It imports only from `novel_ralph_skill.state` and
`novel_ralph_skill.contract.runner`, never from `novel_state`, so command modules
can import *from* it without forming an import cycle (module docstring lines
14-21).

`_draft_read_error(reported_dir: pathlib.Path) -> StateInputError`
(`state_sourcing.py` lines 191-235) is the single source of truth for the
draft-read message. It builds prose naming the `working/` tree and asking for
inspection or repair, and never advises `novel state init` (the tree exists; only
an artefact under it is faulted). It renders from `reported_dir` alone; the caller
keeps the caught exception solely for `raise … from exc` chaining.

The three sites that open-code the guard:

- `novel_ralph_skill/commands/_wordcount.py`,
  `_recount_or_state_error(working_dir, manifest)` (lines 62-103), calls
  `recount_words(working_dir, manifest)` and returns only `by_chapter`.
- `novel_ralph_skill/commands/_recount.py`, `_recount_or_state_error(manifest)`
  (lines 58-97), calls `recount_words(_working_dir(), manifest)` and returns the
  full `(current, by_chapter)` tuple. `_working_dir` here is
  `novel_ralph_skill.commands._state_mutators._working_dir`, which is itself a thin
  alias over `state_sourcing.working_dir()`.
- `novel_ralph_skill/commands/_desloppify.py`, `source_chapters(chapter)` (lines
  164-211), wraps a `ScannedChapter` comprehension over
  `_chapter_text(working_dir, number)` in the `try/except` tail;
  `load_or_state_error` and `_select_chapters` (the exit-3 state-load and exit-2
  usage faults) sit *before* the `try` and stay outside the guard.

`recount_words` (`novel_ralph_skill/state/wordcount.py` lines 86-128) and
`_chapter_text` (`_desloppify.py` lines 82-122) both absorb the one benign read
fault — an absent `draft.md` returns `0`/`""` — and propagate every other read
fault for the command layer to translate. The guard therefore only ever sees the
non-benign faults.

Existing tests that pin the behaviour the change must not move:

- `tests/test_draft_read_message_parity.py` drives all six draft-read boundaries
  from a corrupt-draft tree and asserts each surfaces the one formatter-owned
  remedy clause and exits `3`. This is the load-bearing cross-boundary guard.
- `tests/test_draft_read_message_unit.py` and
  `tests/test_draft_read_message_bdd.py` pin the `_draft_read_error` message
  itself.
- `tests/test_wordcount_command.py` pins `wordcount`'s exit-3 routes (absent
  `working/`, unparseable `state.toml`, undecodable `draft.md`).
- `tests/test_recount_unit.py`, `tests/test_recount_actionable_unit.py`,
  `tests/test_recount_bdd.py` pin `recount`'s routes.
- `tests/test_desloppify_sourcing.py`, `tests/test_desloppify_command.py` pin
  `desloppify`'s exit-2 vs exit-3 split.
- `tests/test_wordcount_e2e.py`, `tests/test_recount_e2e.py`,
  `tests/test_desloppify_e2e.py` prove the installed binary exits `3` on a bad
  `state.toml` through a `cuprum` catalogue. These exercise the same exit-3 path
  the guard sits on; they invoke the installed console script and are unchanged
  by an internal control-flow refactor.
- `tests/test_state_sourcing_home.py` pins the neutral-home properties of
  `state_sourcing` (public seam, no command imports the seam from `novel_state`).

`tests/_state_layout_scanner.py` and `tests/test_multiplexer_mount_table.py` are
in-repo examples of `ast`-walk structural tests; the new anti-drift test (WI5)
follows that pattern to assert the three command modules no longer open-code the
guard.

## Plan of work

Each work item is independently committable and gate-passable. Run `make all`
before committing each. The markdown-only work item (WI6) additionally runs `make
markdownlint` and `make nixie`.

### Stage B/C — the shared guard (WI1)

WI1 adds the context manager to `state_sourcing.py`. This is the only new
production surface; everything after delegates to it.

### Stage C — migrate the three sites (WI2, WI3, WI4)

WI2-WI4 each route one command through the guard, in dependency order (`_recount`
first because it has the cleanest single-reader body, then `_wordcount`, then
`_desloppify`'s comprehension). Each is a small, isolated diff with its own tests.

### Stage D — harden and document (WI5, WI6)

WI5 pins the single-home property structurally. WI6 records the consolidation in
the developers' guide.

---

#### WI1 — Add `draft_read_guard` to `state_sourcing.py`

Implements: roadmap 7.3.3 ("Promote a single … `state_error_on(...)` context
manager into the shared command home … keeping the one exit-`3` fault-routing rule
in a single place"); design §3.2 (exit-`3` channel); developers-guide "The exit-3
messages are actionable" paragraph; AGENTS.md "Use functions and composition";
`.rules/python-context-managers.md`.

Docs to read first: `docs/novel-ralph-harness-design.md` §3.2; this repo's
`.rules/python-context-managers.md`,
`.rules/python-exception-design-raising-handling-and-logging.md`,
`.rules/python-typing.md`; `docs/developers-guide.md` lines 634-682;
`docs/issues/audit-6.1.1.md` Finding 1.

Skills to load: `python-router` (route to `python-abstractions` for the
context-manager shape and `python-errors-and-logging` for the re-raise/`from`
discipline); `python-verification` then `crosshair` for the symbolic check
described below; `leta` for navigation; `sem` for history.

Change: in `novel_ralph_skill/commands/state_sourcing.py`, add near the
`_draft_read_error` formatter:

```python
# novel_ralph_skill/commands/state_sourcing.py
import collections.abc as cabc
import contextlib


@contextlib.contextmanager
def draft_read_guard(reported_dir: pathlib.Path) -> cabc.Iterator[None]:
    """Translate a draft-read fault under ``reported_dir`` to exit ``3``.

    Wrap a chapter-draft read in this guard so any member of
    :data:`STATE_INPUT_ERRORS` it raises is re-raised as the actionable exit-``3``
    :class:`StateInputError` that :func:`_draft_read_error` builds, chaining the
    caught exception via ``from`` so the ``messages`` channel carries only the
    actionable prose. It is the single home for the
    ``try/except STATE_INPUT_ERRORS → _draft_read_error`` shell the draft-read
    boundaries share (roadmap 7.3.3), so an undecodable or unreadable ``draft.md``
    reaches exit ``3`` (design §3.2) and cannot escape to the benign exit ``1``.

    It does not absorb the benign absent-``draft.md`` fault: the readers
    (:func:`~novel_ralph_skill.state.recount_words`,
    :func:`~novel_ralph_skill.commands._desloppify._chapter_text`) already return
    ``0``/``""`` for a missing file, so it never reaches this guard.

    Examples
    --------
    Route a recount's read fault to exit ``3`` naming the working tree::

        with draft_read_guard(working_dir):
            current, by_chapter = recount_words(working_dir, manifest)
    """
    try:
        yield
    except STATE_INPUT_ERRORS as exc:
        raise _draft_read_error(reported_dir) from exc
```

Add `"draft_read_guard"` to `__all__` (it is public, like `load_or_state_error`:
the three command modules import it). Place `import contextlib` with the existing
imports. With `from __future__ import annotations` already at the top of the
module, the `cabc.Iterator[None]` annotation is a string, so keep
`import collections.abc as cabc` under the existing `TYPE_CHECKING` block to avoid
a runtime import; confirm `ty` and Ruff are satisfied (if either evaluates the
annotation, promote the import to module scope).

Tests to add (`tests/test_draft_read_guard_unit.py`, new file):

- Unit (pytest): entering the guard and raising each representative member of
  `STATE_INPUT_ERRORS` inside the `with` block re-raises `StateInputError` whose
  single `messages` entry equals `_draft_read_error(reported_dir).messages[0]` and
  whose `__cause__` is the original exception. Parametrize over a representative
  fault set: `UnicodeDecodeError` (the `ValueError` subclass a bad-UTF-8 body
  raises), `PermissionError` (an `OSError`), and `KeyError`.
- Unit: a clean `with draft_read_guard(reported_dir): pass` raises nothing.
- Unit: an exception *not* in `STATE_INPUT_ERRORS` (e.g. `RuntimeError`)
  propagates unchanged out of the guard (the guard catches only the tuple).
- Verification (CrossHair `diffbehavior`, optional but recommended): write a tiny
  reference function that re-spells the old inline shell (`try: f(); except
  STATE_INPUT_ERRORS as exc: raise _draft_read_error(d) from exc`) and use
  `crosshair diffbehavior` to confirm the guard and the reference agree on the
  raised type and message. If CrossHair cannot reason over the exception classes
  cleanly, fall back to the parametrized unit test above as the pinning adversary
  and record that in the test docstring (per AGENTS.md, property/verification
  tooling is used "when a change introduces an invariant over a range of inputs";
  here the invariant is small and enumerable, so the parametrized unit test is
  sufficient and CrossHair is a belt-and-braces check, not load-bearing).

Validation: `make all`. The new unit test fails before the guard exists (import
error / `AttributeError`) and passes after.

Acceptance: `state_sourcing.draft_read_guard` exists, is in `__all__`, and the new
unit suite is green. `state_sourcing.py` remains ≤ 400 lines (confirm with
`wc -l`).

---

#### WI2 — Route `_recount._recount_or_state_error` through the guard

Implements: roadmap 7.3.3 success criterion ("`recount` … delegate[s] to it
rather than each open-coding the `try/except STATE_INPUT_ERRORS` tail"); design
§3.2; §4.1.

Docs to read first: `docs/novel-ralph-harness-design.md` §4.1 (the `recount`
mutator); `_recount.py` docstrings.

Skills to load: `python-router` → `python-errors-and-logging`; `leta` (use
`leta refs _recount_or_state_error` to confirm the only caller is `recount()`).

Change: in `novel_ralph_skill/commands/_recount.py`, import `draft_read_guard`
from `state_sourcing` (and remove the now-unused `STATE_INPUT_ERRORS` /
`_draft_read_error` imports if they become unused — confirm with `leta`/Ruff), and
rewrite `_recount_or_state_error` to resolve `_working_dir()` once and wrap the
reader in the guard (Decision D4):

```python
# novel_ralph_skill/commands/_recount.py
def _recount_or_state_error(
    manifest: cabc.Sequence[ChapterEntry],
) -> tuple[int, cabc.Mapping[str, int]]:
    working_dir = _working_dir()
    with draft_read_guard(working_dir):
        return recount_words(working_dir, manifest)
```

Update the docstring to say it delegates the fault translation to the shared
`draft_read_guard` (single-home), preserving the existing prose about which faults
are benign vs exit-3.

Tests to add/update:

- The existing `tests/test_recount_unit.py` /
  `tests/test_recount_actionable_unit.py` / `tests/test_recount_bdd.py` exit-3
  cases must stay green unchanged. If any constructs the wrapper directly, confirm
  the `tuple[int, Mapping]` return is preserved.
- Add (or extend an existing unit test) one assertion that a corrupt first-chapter
  `draft.md` drives `recount()` (or `_recount_or_state_error`) to a
  `StateInputError` whose message names the `working/` tree — proving the guard
  is wired, not just present. Prefer extending
  `tests/test_recount_actionable_unit.py`
  if it already exercises an exit-3 path, to avoid a redundant new file.

Validation: `make all`. Acceptance: `recount` exits `3` with the unchanged
actionable message on a corrupt draft; the `recount` suite is green.

---

#### WI3 — Route `_wordcount._recount_or_state_error` through the guard

Implements: roadmap 7.3.3 success criterion ("`wordcount` … delegate[s] to it");
design §3.2; §4.5 (the `wordcount` report).

Docs to read first: `docs/novel-ralph-harness-design.md` §4.5; `_wordcount.py`
docstrings.

Skills to load: `python-router` → `python-errors-and-logging`; `leta`.

Change: in `novel_ralph_skill/commands/_wordcount.py`, import `draft_read_guard`
from `state_sourcing`, drop the now-unused `STATE_INPUT_ERRORS` /
`_draft_read_error` imports if Ruff flags them, and rewrite
`_recount_or_state_error` to wrap the reader, returning only `by_chapter`:

```python
# novel_ralph_skill/commands/_wordcount.py
def _recount_or_state_error(
    working_dir: pathlib.Path,
    manifest: cabc.Sequence[ChapterEntry],
) -> cabc.Mapping[str, int]:
    with draft_read_guard(working_dir):
        _current, by_chapter = recount_words(working_dir, manifest)
    return by_chapter
```

The `return by_chapter` is *outside* the `with` so the body the guard scopes is
just the reader call; the unpacking that cannot raise a `STATE_INPUT_ERRORS`
member sits inside the `with` only because it consumes the reader's result, which
is harmless. Keeping the `return` outside also keeps the guard body to a single
statement (consistent with WI5's structural assertion). Update the docstring to
record the delegation.

Tests to add/update: the existing `tests/test_wordcount_command.py` exit-3 cases
(absent `working/`, unparseable `state.toml`, undecodable `draft.md`) must stay
green unchanged. Confirm `tests/test_wordcount_snapshots.py` and
`tests/test_wordcount_report.py` are unaffected (they exercise the pure report,
not the guard).

Validation: `make all`. Acceptance: `wordcount` exits `3` with the unchanged
message on a corrupt draft; the `wordcount` suite is green.

---

#### WI4 — Route `_desloppify.source_chapters` through the guard

Implements: roadmap 7.3.3 success criterion ("`desloppify` … delegate[s] to it");
design §3.2; §4.4/§5.1.

Docs to read first: `docs/novel-ralph-harness-design.md` §4.4, §5.1;
`_desloppify.py` docstrings.

Skills to load: `python-router` → `python-errors-and-logging`,
`python-iterators-and-generators` (the read body is a comprehension inside the
`with`); `leta`.

Change: in `novel_ralph_skill/commands/_desloppify.py`, import `draft_read_guard`
from `state_sourcing`, drop the now-unused `STATE_INPUT_ERRORS` /
`_draft_read_error` imports if Ruff flags them, and rewrite the tail of
`source_chapters` so only the comprehension is inside the guard, leaving
`load_or_state_error` and `_select_chapters` outside it (Risk R2):

```python
# novel_ralph_skill/commands/_desloppify.py
def source_chapters(chapter: int | None) -> tuple[ScannedChapter, ...]:
    working_dir = pathlib.Path(WORKING_DIR_NAME)
    state = load_or_state_error(working_dir / "state.toml")
    selected = _select_chapters(state.chapters, chapter)
    with draft_read_guard(working_dir):
        return tuple(
            ScannedChapter(
                number=entry.number,
                text=_chapter_text(working_dir, entry.number),
            )
            for entry in selected
        )
```

The `return tuple(...)` stays inside the `with` because the comprehension's draft
reads are exactly the faults the guard must catch; `tuple(...)` forces them
eagerly inside the `with` (a lazy generator would defer the reads past the `with`
and escape the guard — do not convert the comprehension to a generator passed
out). Update the docstring to record the delegation, preserving the prose that the
bad-`--chapter` (exit 2) and bad-`state.toml` (exit 3 via `load_or_state_error`)
faults sit outside the guard.

Tests to add/update: the existing `tests/test_desloppify_sourcing.py` and
`tests/test_desloppify_command.py` must stay green unchanged — in particular the
cases that prove a bad `--chapter` is exit `2` (outside the guard) and a corrupt
draft is exit `3` (inside the guard). Confirm
`tests/test_desloppify_finding_message.py` and the snapshot suite are unaffected.

Validation: `make all`. Acceptance: `desloppify` keeps its exit-2 vs exit-3 split;
a corrupt draft exits `3` with the unchanged message; the `desloppify` suite is
green.

---

#### WI5 — Structural single-home anti-drift test

Implements: roadmap 7.3.3 definition of done ("a test pins it so it cannot
silently re-fork"); AGENTS.md "Duplicated code" heuristic.

Docs to read first: `tests/_state_layout_scanner.py`,
`tests/test_state_sourcing_home.py`, and `tests/test_multiplexer_mount_table.py`
(the in-repo `ast`-walk patterns).

Skills to load: `python-router` → `python-testing`; `leta`.

Change: add `tests/test_draft_read_guard_home.py`. Using `ast` (not raw substring
matching — follow the `_state_layout_scanner.py` / `test_state_sourcing_home.py`
pattern), assert the single-home property over the three migrated command modules
(`_wordcount.py`, `_recount.py`, `_desloppify.py`):

- Each migrated module imports `draft_read_guard` from
  `novel_ralph_skill.commands.state_sourcing`.
- No migrated module contains an `ast.ExceptHandler` whose caught type is
  `STATE_INPUT_ERRORS` that re-raises a call to `_draft_read_error(...)` — i.e.
  the open-coded guard shell is gone. Detect this by walking each module's `ast`
  for an `ExceptHandler` whose `type` is the `Name` `STATE_INPUT_ERRORS` and
  whose body raises a call to `_draft_read_error`; assert none remain in the
  three modules.
  Phrase the scanned set so the three *out-of-scope* modules
  `_novel_done`/`_compile` are **not** included (Decision D2) — record in a comment
  that they are a later slice, so the test does not falsely fail on their
  still-open-coded shells.
- `state_sourcing.draft_read_guard` is public (no leading underscore) and in
  `state_sourcing.__all__` (mirror `test_state_sourcing_home.py`'s public-seam
  assertion rather than duplicating its whole module-scan).

Tests to add: the file above. It fails before WI2-WI4 migrate the sites (the
open-coded handlers still exist) and passes after.

Validation: `make all`. Acceptance: the structural test is green and would fail
if any of the three sites re-grew the inline guard.

---

#### WI6 — Document the consolidation in the developers' guide

Implements: AGENTS.md "Documentation maintenance" / "Abstraction … helper policy"
("Document the new abstraction's intended scope and re-use policy. Record the
decision in … developers-guide docs"); roadmap 7.3.3 definition of done ("it is
documented as the single source of truth").

Docs to read first: `docs/developers-guide.md` lines 634-682 (the existing exit-3
formatter prose, which already documents `_draft_read_error` and the
`state_sourcing` home); `docs/documentation-style-guide.md`.

Skills to load: `en-gb-oxendict` (prose spelling); review the markdown-wrap rule
(80 columns for prose) in AGENTS.md "Markdown guidance".

Change: in `docs/developers-guide.md`, extend the `_draft_read_error` paragraph
(around lines 640-646) or add a short sibling paragraph recording that the
`try/except STATE_INPUT_ERRORS → _draft_read_error` *guard* is now homed in the
`state_sourcing.draft_read_guard` context manager, that `wordcount`, `recount`,
and `desloppify` delegate to it, and that the three other draft-read boundaries
(`novel done`, both `novel compile` tails) still open-code the shell pending a
later slice (so a reader is not surprised they differ). Keep prose wrapped at 80
columns; do not wrap headings or tables.

Tests/validation: `make markdownlint` and `make nixie` (markdown gates), then
`make all` (the markdown change does not affect code, but run the full gate to be
safe). Acceptance: `make markdownlint` and `make nixie` pass; the guide names
`draft_read_guard` as the single home for the guard.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-3-3`.

1. WI1: edit `novel_ralph_skill/commands/state_sourcing.py`; add
   `tests/test_draft_read_guard_unit.py`. Run `make all`. Commit.

   ```bash
   make all
   wc -l novel_ralph_skill/commands/state_sourcing.py   # expect <= 400
   ```

2. WI2: edit `novel_ralph_skill/commands/_recount.py`; update its recount tests.
   Run `make all`. Commit.

3. WI3: edit `novel_ralph_skill/commands/_wordcount.py`; confirm wordcount tests.
   Run `make all`. Commit.

4. WI4: edit `novel_ralph_skill/commands/_desloppify.py`; confirm desloppify
   tests. Run `make all`. Commit.

5. WI5: add `tests/test_draft_read_guard_home.py`. Run `make all`. Commit.

6. WI6: edit `docs/developers-guide.md`. Run `make markdownlint`, `make nixie`,
   then `make all`. Commit.

Expected transcript shape for `make all` (abbreviated):

```plaintext
$ make all
... ruff format --check ... (check-fmt) OK
... ruff check ... interrogate ... pylint ... (lint) OK
... ty check ... (typecheck) OK
... pytest -v -n ... (test) N passed
```

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes; the new/extended tests
  (`tests/test_draft_read_guard_unit.py`, `tests/test_draft_read_guard_home.py`,
  and the per-command exit-3 assertions) fail before their work item and pass
  after. Every existing suite named in Context — especially
  `tests/test_draft_read_message_parity.py` and the three e2e suites — stays green
  with no edit.
- Lint/typecheck: `make lint` and `make typecheck` pass; 100% docstring coverage
  (the new context manager carries a numpydoc docstring with an example).
- Behaviour: each of `wordcount`, `recount`, `desloppify` exits `3` with the
  identical actionable message on a corrupt `draft.md`, and exits `1`/`0`/`2`/`4`
  exactly as before on every other path. No observable output moves.
- Markdown: `make markdownlint` and `make nixie` pass for the developers-guide
  change.

Quality method (how we check): run `make all` after every work item and the two
markdown gates after WI6. The structural test (WI5) is the standing guard that the
consolidation cannot silently re-fork.

## Idempotence and recovery

Every work item is a self-contained edit plus its tests, committed separately, so
re-running `make all` on any committed state is safe and repeatable. No step is
destructive; there are no migrations, no data writes, no network calls. If a work
item's `make all` fails, fix forward within the iteration tolerance (3 attempts)
or revert that single commit and escalate.

## Artefacts and notes

The load-bearing existing test that proves behaviour is unchanged is
`tests/test_draft_read_message_parity.py`: it drives all six draft-read boundaries
from a corrupt-draft tree and asserts each surfaces the one formatter-owned remedy
clause and exits `3`. It must stay green with no edit through every work item —
that is the strongest single signal that the consolidation preserved behaviour.

## Interfaces and dependencies

At the end of the slice these names must exist with these signatures:

In `novel_ralph_skill/commands/state_sourcing.py`:

```python
@contextlib.contextmanager
def draft_read_guard(reported_dir: pathlib.Path) -> collections.abc.Iterator[None]:
    ...
```

and `"draft_read_guard"` is a member of `state_sourcing.__all__`.

The three command modules import it as `from
novel_ralph_skill.commands.state_sourcing import draft_read_guard` and use it as
`with draft_read_guard(working_dir): ...`, with no remaining open-coded
`try/except STATE_INPUT_ERRORS → _draft_read_error` handler.

No new external dependency is introduced; the change uses only the standard
library (`contextlib`, `collections.abc`) and the existing in-repo `state_sourcing`
symbols. The locked `cuprum` 0.1.0 surface the e2e suites use (`cuprum.sh.make`,
`cuprum.program.Program`, `cuprum.sh.ExecutionContext`, `run_sync(capture=True)`,
and the `single_program_catalogue` fixture whose registration is the execution
gate via `catalogue.lookup` raising `UnknownProgramError`) is untouched — verified
against the locked install at `cuprum/sh.py` (`make`, `ExecutionContext`,
`run_sync`, `capture`) and `cuprum/catalogue.py` (`ProgramCatalogue.lookup`) —
because this refactor changes only internal Python control flow, not how any
binary is invoked.

## Revision note

Round 1 (2026-06-27): initial draft. Replaces the stale "direct-edit guard"
ExecPlan that previously occupied this filename (that task was renumbered to
roadmap 7.6.3 and is recoverable from git history at commit `b28eaad`). Pins the
consolidation mechanism to a `contextlib.contextmanager` `draft_read_guard` homed
in `state_sourcing` (Decision D1), scopes the migration to the three roadmap-named
commands (Decision D2), and verifies the locked `cuprum` 0.1.0 e2e surface is
untouched. No implementation performed.
