# Logisphere design review — roadmap-2-1-2 ExecPlan, round 2

Status: REVISE. Reviewer: adversarial Logisphere crew.

The round-2 revision resolves two of the three round-1 blockers cleanly and the
third only partially. B1 (gate-ratio numerator) and B2 (entry-point rewiring)
are now correct and verified against the real corpus oracle, the specs, the
variants, and the registry gates. B3 is half-resolved: the `--human` pre-parse
is legitimate and ADR-cited, but the plan invents an uncited `--working-dir`
command-line flag, mis-attributes it to ADR-003, and elevates it to a
cross-command convention the design never sanctioned. Two consequential gaps
(the `build_app()` data-flow and the stub/e2e narrowing) follow from it.

## Confirmed-resolved (round-1 blockers, verified against source)

- **B1 (gate-ratio quantity) — RESOLVED.** Verified: no corpus variant sets
  `by_chapter_override` (`_variants.py` never assigns it), so
  `sum(state.word_counts.by_chapter.values())` equals the oracle's
  `sum(chapter.draft_words)` on every tree (`_specs.py::derive_by_chapter`).
  On `by-chapter-sum-mismatch` (`current_words_override=1`, drafts and gate
  booleans intact) the validator now names exactly `{by-chapter-sum}`, matching
  the oracle. The drafted-total numerator decouples invariant 7 from invariant
  3. Work item 4's strict restricted-set equality will hold. The prior
  "current/target isolates 7 from 3" reasoning was correctly removed.
- **B2 (entry-point) — RESOLVED.** Verified: `names.py` binds all five entry
  points to `STUB_MODULE` and `project_scripts_table()` derives
  `[project.scripts]` from it. Keeping `novel-state` on `stub.py::novel_state()`
  (evolved in place) leaves the three registry gates
  (`test_registry_matches_project_scripts`, `test_registry_order_matches_table`,
  `test_entry_points_resolve_to_callables`) valid, since the last only asserts
  `callable(getattr(stub, func))`. The Wafflecat alternative from round 1 was
  adopted correctly.

## Blocking defects (round 2)

### B4 (Telefono / Pandalump) — the `--working-dir` flag is an uncited, unneeded contract-surface invention mis-attributed to ADR-003

The plan asserts (Context item 6; B3 Decision Log; Work item 2) that "ADR-003
§3.1 and design §3.1 mandate a `--human` switch and a `working_dir` in every
envelope" and from this derives a global `--working-dir VALUE` command-line
flag that it threads through `RunContext` and establishes as "the convention all
four later commands inherit".

Verified against source, this conflates two different things:

- ADR-003 §3.1 mandates a `--human` flag and a `working_dir` **envelope field**.
- The design shows `working_dir` as the fixed constant `"working"` (design line
  151) — a cwd-relative subdirectory. Exit `3` is defined as "working dir
  absent" (design line 189), i.e. `./working/` does not exist.
- A repository-wide search (`docs/novel-ralph-harness-design.md`,
  `docs/users-guide.md`, all `docs/adr-*.md`) finds **no `--working-dir` flag,
  no `--working` option, and no per-invocation working-directory override**
  anywhere. The only occurrences of `working_dir` are the envelope field.

So `--working-dir` is the plan's own invention, presented as ADR-mandated. Per
the task's standing rule, an uncited memory-based claim about a locked contract
surface is a blocking defect: the plan must either cite the design/ADR text that
sanctions a `--working-dir` CLI flag (none exists) or drop it.

It is also **unnecessary**. The established corpus pattern materialises a tree
under `tmp_path` and returns the `working/` path (`build_tree`, `baseline_tree`,
`incoherent_tree` all build `dest/working/`). The behavioural suite can point
`check` at a fixture by `monkeypatch.chdir(dest)` and relying on the default
`working/`, exactly matching the design's fixed `working_dir="working"` — no new
flag, no new cross-command CLI surface. The legitimate, ADR-backed part of B3
(pre-parsing `--human` off argv before `run`, because `run` stamps the envelope
on the body-less exit-2/exit-3 paths) stands; only the `--working-dir` portion
is the defect.

Resolution required: drop `--working-dir` (and its "convention all four later
commands inherit" framing), or escalate it as a genuine design decision with a
design/ADR amendment. Keep the `--human` pre-parse, which `runner.py` confirms
is required (the envelope is emitted from `context` on the exit-2/exit-3 paths
before any body runs).

### B5 (Pandalump / Doggylump) — `build_app()`'s zero-arg signature cannot deliver the resolved working directory to the `check` body

The Interfaces section pins `def build_app() -> cyclopts.App` (no parameters)
as a stable public surface later tasks import. Separately, the `check` body
"is given the resolved working directory (a `pathlib.Path`) by the entry point"
and the plan strips the global tokens off argv **before** `run`, so the residual
argv passed to `app()` no longer contains any working-directory token.

These two statements are mutually inconsistent. The established wiring
(`conftest.py::wrapper_app`) injects per-invocation data into a subcommand body
via a **closure captured by the builder** — but that requires the builder to
receive the value (`build_app(working_dir)`), which the pinned zero-arg
signature forbids. The plan's escape hatch — "via a closure or a Cyclopts
default" — does not work as written: the closure has nothing to close over
because `build_app()` takes no argument, and the Cyclopts-default path requires
the token to remain in the residual argv (the plan removed it). A novice
following the plan literally has **no mechanism** to get `working_dir` into the
`check` body.

Resolution required: make the data flow concrete and consistent. Either give
`build_app(working_dir: Path)` a parameter (and update the Interfaces signature
and the WI2 wiring), or have `check` resolve `./working/` from cwd itself
(consistent with dropping `--working-dir` per B4). Pin the chosen mechanism in
the Interfaces section rather than offering two non-working alternatives.

### B6 (Doggylump) — the stub/e2e narrowing is under-specified; `novel_state()` now exits 3 (not 2) with no `working/`, and the plan does not enumerate which gates break or how the new e2e is built

Work item 2 says to "narrow any 'all five commands exit 2' assertion in the
stub/e2e suites to the four still-stubbed commands". Verified against the gates,
this is directionally right but materially incomplete:

- `test_command_stubs.py::test_command_result_exits_two`,
  `::test_unknown_option_exits_one`, and `::test_meta_flags_exit_zero` call
  `stub.make_stub_app(name)` directly and are **unaffected** (the factory is
  untouched). The plan implies these need narrowing; they do not.
- `test_command_stubs.py::test_entry_point_callable_exits_two` is parametrized
  over the real `ENTRY_POINTS` and calls `novel_state()` with a clean argv.
  After WI2, `novel_state()` runs `run(...)` against `./working/`, which does
  not exist in the test's cwd, so `load_state` raises and the command exits
  **`3`, not `2`**. This test breaks and must be narrowed — but the plan never
  states the new exit code is `3`, so a reader cannot predict the failure mode.
- `test_console_scripts_e2e.py::_assert_scripts_exit_two` runs the **installed**
  `novel-state` with no args and asserts exit `2`; post-WI2 it exits `3`.
  Narrowing it touches a cuprum-driven, `@pytest.mark.slow`,
  `@pytest.mark.timeout(180)` e2e governed by ADR-006. The plan's one-line
  "include at least one subprocess invocation through the installed
  console-script" does not specify that the new `novel-state` e2e needs an
  on-disk `working/` tree materialised in the subprocess cwd, nor that the
  global `timeout = 30` (pyproject line 325) applies unless overridden, nor how
  the cuprum `single_program_catalogue` invocation sets the subprocess cwd to a
  directory containing `working/`.

Resolution required: enumerate the exact assertions that break and their new
exit codes (`test_entry_point_callable_exits_two` and the e2e both move to `3`
for `novel-state` unless a `working/` tree is present), and specify how the new
`novel-state` e2e materialises a coherent `working/` tree in the subprocess cwd
and which timeout marker it carries. Otherwise WI2 cannot be implemented to
green without on-the-fly redesign.

## Advisory (non-blocking, but address)

- A1 (Pandalump) — the oracle's `_check_cursor_coherent` enforces
  `0 <= current_chapter`; the plan's validator clause (Work item 1) is only
  `current_chapter <= len(state.chapters)` and `current_scene/beat >= 0`. No
  corpus variant and no constructed Hypothesis state produces a negative
  `current_chapter`, so agreement holds, but the validator should also assert
  `current_chapter >= 0` to match the oracle's structural reading and avoid a
  silent gap when task 2.1.3 cross-checks against arbitrary on-disk states.

- A2 (Telefono) — the `check` body's exit-3 exception set
  (`FileNotFoundError`/`OSError`/`TOMLDecodeError`/`KeyError`/`ValueError`) omits
  `TypeError`, which `parse_state` can raise on a structurally wrong table. The
  two tested faults (missing file → `FileNotFoundError`; `not = toml =` →
  `TOMLDecodeError`) are covered, so this is not blocking, but record `TypeError`
  in the mapping or justify its exclusion.

- A3 (Buzzy Bee / Dinolump) — a hand-rolled `parse_global_flags` that must
  coexist with Cyclopts subcommand parsing is fragile at the edges
  (`--working-dir` with no value, flag-in-any-position vs the Constraints'
  "leading/trailing", `--working-dir=VALUE` vs `--working-dir VALUE`). Dropping
  `--working-dir` (B4) shrinks this to a single `--human` boolean strip, which
  is far less error-prone. If `--human` alone is retained, pin its exact parse
  semantics (a boolean flag removed from argv in any position) with the unit
  tests the plan already lists.

## Verified-correct (the planner did this well in round 2)

- B1 and B2 resolutions verified against `_oracle.py`, `_specs.py`,
  `_variants.py`, `names.py`, `stub.py`, and the registry gates.
- All asserted schema field paths confirmed: `state.phase.current/.completed`;
  `state.word_counts.current/.target/.by_chapter`;
  `state.drafting.critic.consecutive_clean/.convergence_target`;
  `state.drafting.current_chapter/.current_scene/.current_beat`;
  `state.gates.knitting.done_30/.done_50/.done_80`; `state.chapters`;
  `Phase`/`PHASE_ORDER`; `load_state` at parse.py:228.
- The six owned invariant-name strings match `CORPUS_INVARIANT_NAMES` exactly
  (`_oracle.py` lines 37–55), and developers-guide lines 115–118 confirm task
  2.1.2 keys on them.
- The consecutive-clean manifest-length proxy and the two bijection variants'
  cursor agreement were re-verified: `_BASE.current_chapter = 3 = len(chapters)`,
  and neither bijection variant perturbs the cursor, so the manifest-vs-on-disk
  divergence on those variants does not break cursor-coherent agreement.
- Exit-4-on-violation, exit-3-on-state-fault, checker-no-write, and the
  pure-state/disk-evidence scope split match design §3.2/§3.3/§4.1/§5.2/§5.4 and
  the roadmap decomposition (2.1.2 vs 2.3.2).
- Hypothesis (not CrossHair/mutmut) is the right adversary per design §2.3 and
  `uv.lock`; `cuprum` correctly out of scope (verified against
  `/data/leynos/Projects/cuprum/cuprum/catalogue.py`, an executable allowlist);
  no new dependency.

## Pre-mortem (most likely failure path)

Six months on: a developer implements WI2 literally — pins `build_app()` at
zero args, strips `--working-dir` off argv before `run` — and discovers at
implementation time that the `check` body has no resolved working directory.
Under pressure they wire `check` to re-read `sys.argv` or re-`chdir` inside the
body, splitting the working-directory source of truth between the entry point
(which stamps the envelope) and the body (which reads the file). The envelope's
`working_dir` and the file actually read drift apart on the very first command
that exercises the real `run` path, and because the plan made `--working-dir`
the "convention all four later commands inherit", the split propagates to
2.2.2/2.3.x. Prevention: resolve B4 (drop the invented flag, read `./working/`
from cwd) and B5 (one concrete data-flow mechanism), so the working directory
has exactly one source of truth before this becomes a cross-command contract.

## Strongest alternative (Wafflecat)

Drop `--working-dir` entirely and let `novel-state check` operate on
`./working/` relative to the process cwd, exactly as the design's fixed
`working_dir="working"` field implies. The entry point pre-parses only the
ADR-mandated `--human` boolean; the `check` body forms `Path("working") /
"state.toml"`. Behavioural and e2e tests select a fixture by `chdir`-ing into
the materialised parent directory (the corpus fixtures already return
`dest/working/`). This trades the plan's "explicit working-dir override" for
strict design conformance, a one-flag pre-parse, zero new cross-command CLI
surface, and a single source of truth for the working directory — and it removes
the root cause of B4, B5, and most of A3 at once. If a working-directory
override is genuinely wanted later, it should be raised as a design/ADR change,
not introduced as a side effect of the first command's plan.

## Verdict

REVISE. B1 and B2 are correctly resolved and verified. B3 is only half-resolved:
the `--working-dir` flag (B4) is an uncited, design-non-conformant, and
unnecessary contract-surface addition; B5 (the `build_app()` data-flow) and B6
(the stub/e2e narrowing specifics) follow from it. Adopting the Wafflecat
alternative — cwd-relative `working/`, `--human`-only pre-parse — resolves all
three blockers and leaves the plan implementable and design-conformant.
