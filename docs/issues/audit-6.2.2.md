# Post-merge audit: roadmap task 6.2.2

Audit of the codebase after roadmap task 6.2.2 ("build the end-to-end
per-chapter deterministic-loop scenario", commit `717782b`) merged to `main`.
The task added the in-process per-chapter loop feature
(`tests/features/per_chapter_loop.feature`) and its steps
(`tests/steps/per_chapter_loop_steps.py`, bound by
`tests/test_per_chapter_loop_bdd.py`), the installed-binary re-drive
(`tests/features/per_chapter_loop_installed.feature`,
`tests/steps/per_chapter_loop_installed_steps.py`, bound by
`tests/test_per_chapter_loop_installed_bdd.py`), and a developers'-guide section.
It drives the deterministic spine — `recount`, `novel-done`, `wordcount`,
`desloppify`, and `novel-compile --check` — as one ordered drive over a real
`working_corpus` tree through the shared `run` boundary, plus three focused
gated-decision scenarios (stale compile, crossed knitting gate, refused
out-of-order advance) and an installed re-drive at the wheel/venv boundary.

The change is sound and the roadmap success clause is met: the spine is driven
through the shared command boundary (not body calls), the gated decisions are
each pinned over the corpus tree that exhibits exactly that decision, and the
installed re-drive proves the harness-trusted exit codes at the real packaging
boundary with a wheel-free mark-retention guard. The findings below are not
regressions; they are duplication and locality drift introduced or reinforced by
6.2.2's two new step modules, plus a small number of coverage and consistency
gaps. None block the merge.

Sources relied on: `docs/novel-ralph-harness-design.md` (§3.2 exit codes, §3.3
checker/mutator split, §4.1-§4.5 command bodies, §5.4 disk evidence, §7.2
Figure 3 the per-chapter loop, §9 lines 814-847 the loop success criteria, §10
failure modes), `docs/adr-003-shared-interface-contract.md`,
`docs/adr-006` (the POSIX-only installed boundary), `docs/developers-guide.md`
("The per-chapter deterministic-loop scenario"), `docs/roadmap.md` (task 6.2.2),
prior audits `docs/issues/audit-6.2.1.md` and `docs/issues/audit-1.2.1.md`, and
`AGENTS.md` (en-GB Oxford spelling, module/file boundaries, snapshot-plus-
semantic rule, the `tests/steps/` assert/argument-count exemption). Loaded the
`python-router` and `python-testing` skills; navigated code with `leta`/`grep`
and traced history with `git show`/`sem` over commit `717782b`.

## Finding 1: The run-and-capture command driver is duplicated across five step modules

- **Category:** duplication
- **Severity:** medium
- **Location:** `tests/steps/per_chapter_loop_steps.py:87-111` (`_run_capturing`),
  `tests/steps/torn_turn_recovery_steps.py:108-132` (`_run`/`_run_capturing`),
  `tests/steps/compile_steps.py:67-97` (`_run_compile`/`_run_check`),
  `tests/steps/advance_phase_steps.py:71-75`, and
  `tests/steps/reconcile_steps.py:83-90`.

Five step modules now re-spell the same in-process command driver: `monkeypatch.
chdir(working.parent)`, then `with contextlib.redirect_stdout(stream),
pytest.raises(SystemExit) as excinfo:` wrapping a `run(build_app(), argv,
RunContext(command=..., working_dir="working", human=False))` call, with the body
either returning `excinfo.value.code` alone or alongside `json.loads(stream.
getvalue() or "{}")`. The 6.2.2 module (`per_chapter_loop_steps._run_capturing`)
produced the most general form of this helper — it parameterizes the `build_app`
factory by `command_name` via `_BUILD_APPS` so a single driver spans all five
read surfaces — yet it remains module-private, so the codebase now carries six
near-identical copies of the SystemExit-capturing seam. `torn_turn_recovery_
steps.py:30-31` already flags this tension explicitly ("kept self-contained
rather than shared ... the helpers are a handful of lines"), but with the 6.2.2
multi-app driver the helpers are no longer a handful of trivial lines, and the
`RunContext(..., working_dir="working", human=False)` literal plus the `or "{}"`
empty-envelope guard are now repeated invariants that could drift apart.

- **Proposed fix:** Promote a single command-driver helper into a shared test
  module (a `tests/command_driver.py` plugin in the existing `pytest_plugins`
  list, mirroring how `conftest.py` already consolidated the cross-module private
  import that "six post-merge audits flagged" per `conftest.py:6-8`). Expose one
  `run_capturing(build_app, argv, *, command, monkeypatch) -> tuple[int, dict]`
  (and a thin code-only wrapper) keyed off the `build_app` factory, and have the
  five step modules import it by name. The 6.2.2 `_BUILD_APPS` registry is the
  natural home for the factory lookup. This removes five copies of the chdir +
  redirect + `pytest.raises(SystemExit)` + `json.loads(... or "{}")` invariant.

## Finding 2: The `result`-block unwrap helper is copied verbatim between the two 6.2.2 modules

- **Category:** duplication
- **Severity:** low
- **Location:** `tests/steps/per_chapter_loop_steps.py:114-117` (`_result`) and
  `tests/steps/per_chapter_loop_installed_steps.py:105-108` (`_result`).

Both 6.2.2 step modules define a `_result(outcome_or_installed, command_name)`
helper whose body is the identical envelope unwrap —
`typ.cast("dict[str, object]", envelope["result"])` after pulling the capture
tuple from the per-command capture map. They differ only in the capture-tuple
arity (the in-process capture is `(code, envelope)`; the installed capture is
`(code, envelope, stderr)`), so the unwrap logic itself is the same fact written
twice. Any change to the envelope shape (for example a future nesting of
`result` under a versioned key) would have to be made in both, and the two could
silently diverge.

- **Proposed fix:** Fold the unwrap into the shared driver of Finding 1 — have
  the driver return a small captured-result value object (or a typed mapping)
  that exposes `.result` once, so both modules read the `result` block through a
  single owned accessor rather than two parallel `_result` functions.

## Finding 3: The drafted total `68800` is hardcoded in both modules rather than derived from the corpus

- **Category:** inconsistency
- **Severity:** medium
- **Location:** `tests/steps/per_chapter_loop_steps.py:59-60`
  (`_DRAFTED_BY_CHAPTER`, `_DRAFTED_TOTAL = 68800`) and
  `tests/steps/per_chapter_loop_installed_steps.py:50` (`_DRAFTED_TOTAL = 68800`).

The clean-pass assertions pin the drafted total `68800` and the per-chapter
table `{"01": 24000, "02": 24000, "03": 20800}` as literals in two places. The
in-process docstring (lines 56-60) states these are "derived from the corpus
`_DRAFTED_WORDS`", but they are not derived — they are transcribed. The corpus
owns the single source of truth at `tests/working_corpus/_library.py:42`
(`_DRAFTED_WORDS = (24000, 24000, 20800)`, summing to 68800, documented at lines
39-40), and that name is module-private (leading underscore), so there is no
public accessor the step modules could route through even if they wanted to.
A change to `_DRAFTED_WORDS` (re-balancing a chapter to keep the gate thresholds)
would leave all three literal sites stale, and the assertions would then pin a
total the corpus no longer produces — a silent desync between the corpus the
tree is built from and the totals the loop asserts.

- **Proposed fix:** Expose a public corpus accessor — e.g. `working_corpus.
  DRAFTED_WORDS` (or `drafted_total()` / `drafted_by_chapter()`) re-exported from
  `working_corpus/__init__.py` — and have both step modules derive `_DRAFTED_
  TOTAL` (`sum(...)`) and `_DRAFTED_BY_CHAPTER` from it. This makes the drafted
  totals the corpus's owned fact, honouring the docstring's "derived from" claim
  and removing the three transcribed literals. Pairs naturally with Finding 4.

## Finding 4: The three-gate `cumulative` assertion block is duplicated across the two modules

- **Category:** duplication
- **Severity:** low
- **Location:** `tests/steps/per_chapter_loop_steps.py:198-204`
  (`wordcount_gates_crossed`) and
  `tests/steps/per_chapter_loop_installed_steps.py:190-196`
  (`installed_wordcount_gates`).

Both modules assert the §4.5 "all three knitting gates crossed" success
criterion with the same four-line block: `cumulative["current"] ==
_DRAFTED_TOTAL` followed by `gate_triggered_30/50/80 is True`. The 30/50/80
gate triple is a domain fact (the design's three knitting thresholds) restated
literally in two test modules; a fourth threshold or a renamed field would need
both edited in lockstep.

- **Proposed fix:** Extract one `assert_all_gates_crossed(cumulative, *, total)`
  helper into the shared test module from Finding 1 and call it from both the
  in-process and installed gate steps, so the "all three gates crossed at the
  drafted total" assertion lives once. The gate field names could be derived from
  a shared `(30, 50, 80)` tuple to make a future fourth gate a one-line change.

## Finding 5: `_run_capturing` couples a query (capture envelope) to a command effect (chdir)

- **Category:** cqs
- **Severity:** low
- **Location:** `tests/steps/per_chapter_loop_steps.py:87-111` (`_run_capturing`)
  and the shared driver this would become under Finding 1.

`_run_capturing` is named and used as a query that returns `(exit_code,
envelope)`, but as a side effect it permanently `chdir`s the process into
`working.parent` (line 102) and never restores it. Within a pytest test the
`monkeypatch` fixture unwinds the cwd at teardown, so this is safe in practice,
but the helper's signature hides a process-wide mutation behind a value-returning
call: a reader of `outcome.captures["recount"] = _run_capturing(...)` cannot see
that the cwd moved. Because every `When` step calls it afresh, each re-`chdir`s
to the same parent, which is idempotent here but would not be if two trees with
different parents were driven in one scenario.

- **Proposed fix:** When consolidating under Finding 1, make the cwd change an
  explicit, scoped effect — accept the run directory and enter it under a
  `contextlib.chdir` context manager (Python 3.11+) for the duration of the
  single `run` call, restoring it on exit — so the helper is a pure query over an
  explicitly scoped working directory rather than a query that quietly leaves the
  process cwd moved.

## Finding 6: The installed clean pass and stale catch share no driver loop with their argv map

- **Category:** ergonomics
- **Severity:** low
- **Location:** `tests/steps/per_chapter_loop_installed_steps.py:55-61`
  (`_LOOP_ARGV`), `:163-167` (`run_installed_clean_spine`), and `:229-238`
  (`run_installed_stale`).

The installed module keeps a `_LOOP_ARGV` registry mapping each command to its
extra argv, and the clean-pass `When` iterates `for command_name in _LOOP_ARGV`
to drive all five. The stale-tree `When`, however, drives `novel-done` and
`novel-compile` by two hand-written `_run_installed` calls (lines 237-238) rather
than over a (sub)set of the same registry, so the two `When` steps express "drive
this list of installed commands" in two different idioms. This is minor, but it
means the set of commands the stale path exercises is implicit in two literal
calls rather than a named subset.

- **Proposed fix:** Drive both `When` steps over an explicit command tuple (the
  full `_LOOP_ARGV` keys for the clean pass; an explicit `("novel-done",
  "novel-compile")` tuple for the stale path), with a single private loop helper
  `_drive(installed, command_names)` that fills the captures. This makes the
  exercised command set a named, readable value in both steps.

## Finding 7: No installed re-drive of the crossed-gate or refused-advance gated decisions

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/features/per_chapter_loop_installed.feature:16-24` (the
  single installed scenario) against `tests/features/per_chapter_loop.feature:38-46`
  (the in-process crossed-gate and refused-advance scenarios).

The installed feature re-drives the clean pass and the stale-compile catch at the
wheel/venv boundary, but two of the four in-process gated decisions — the crossed
knitting gate (§4.5) and the refused out-of-order `advance-phase` (§3.2, §4.1,
exit 3) — are proven only in-process. The exit-3 state-error arm in particular is
stamped by `contract/runner.py` *before* the command body runs (the global-flag
pre-parse), so its behaviour at the installed entry point is plausibly where a
packaging regression (a wrong `sys.exit` translation, a swallowed traceback)
would first show. The developers' guide says the installed re-drive carries the
"clean pass and the stale-compile catch"; it does not say why the other two
decisions are left in-process, so a reader cannot tell whether this is a
deliberate bound or an omission.

- **Proposed fix:** Either add an installed re-drive of the refused-advance
  decision (the highest-value addition, since the exit-3 arm is runner-stamped and
  POSIX exit-code translation is exactly what the installed boundary exists to
  prove) and the crossed-gate assertion, reusing the existing `installed_novel_
  state` wheel fixture; or add one sentence to the developers' guide
  "per-chapter deterministic-loop scenario" section naming the in-process-only
  bound for those two decisions, so it is "carried knowingly rather than silently"
  (design §9).

## Finding 8: The installed module re-spells the design §10 no-traceback rule rather than sharing it

- **Category:** separation-of-concerns
- **Severity:** low
- **Location:** `tests/steps/per_chapter_loop_installed_steps.py:111-118`
  (`_assert_no_traceback`) and `tests/test_console_scripts_e2e.py` /
  `tests/test_recount_e2e.py` (the sibling installed e2es the module docstring
  cites as its model).

`_assert_no_traceback` encodes a design §10 contract — "a finding or state fault
yields a structured message, never a stack trace" — as a `"Traceback" not in
stderr` substring check. The module docstring (lines 16-18) names
`test_console_scripts_e2e.py` and `test_recount_e2e.py` as the installed-e2e
pattern it mirrors; if those modules assert the same no-traceback property, the
contract is now expressed in three places with three independent substring
checks, and the canonical wording of "no stack trace at the boundary" is not
owned by one helper.

- **Proposed fix:** If the sibling installed e2es carry the same check (worth
  confirming when implementing Finding 1), promote a shared `assert_no_traceback(
  stderr, *, command)` into the installed-e2e support module so the §10
  no-stack-trace contract is asserted through one owned helper across every
  installed-boundary suite.

## Finding 9: The §7.2 loop ordering is asserted only by Gherkin step order, not pinned as data

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/features/per_chapter_loop.feature:18-29` (the clean-pass
  scenario's `When`/`Then` ordering) and
  `tests/steps/per_chapter_loop_steps.py` (the per-command capture map, which is
  order-insensitive).

The roadmap clause and design §7.2 (Figure 3) are about the deterministic spine
running in a *fixed order* — `recount` → `novel-done` → `wordcount` →
`desloppify` → `novel-compile --check`. The clean-pass scenario encodes that
order only as the sequence of Gherkin steps; the underlying `_Outcome.captures`
dict is keyed by command name and is wholly order-insensitive, so each command is
in fact driven independently against the same immutable tree, and re-ordering the
feature steps would not change any assertion. This is a reasonable modelling
choice (the read surfaces are independent over a fixed tree), but it means
"the spine composes *in order*" — the headline of the roadmap clause and the
guide — is documented in prose and step sequence rather than asserted.

- **Proposed fix:** Either add one assertion that the loop's branch decision
  follows from the ordered exit codes (e.g. a step asserting the captured
  `(recount, novel-done, wordcount, desloppify, novel-compile)` exit-code tuple
  equals `(0, 0, 0, 0, 0)` as an ordered sequence, making the order load-bearing
  in the assertion), or note in the developers' guide that ordering is modelled
  by step sequence because the five read surfaces are independent over the
  immutable tree, so the "fixed order" claim's scope is explicit.

## Finding 10: Task 6.2.2 re-landed the MD012 markdownlint regression in the dev guide

- **Category:** inconsistency
- **Severity:** medium
- **Location:** `docs/developers-guide.md:113-114` (two consecutive blank lines
  before the `### The per-chapter deterministic-loop scenario` heading the task
  added).

The 6.2.2 commit inserted its new developers'-guide section with two blank lines
before its heading, tripping `MD012/no-multiple-blanks`, so `make markdownlint`
over the whole tree fails on `main` at commit `717782b`. This is the *same*
regression class `docs/issues/audit-6.2.1.md` Finding 6 recorded one task earlier
(a double blank before a freshly inserted guide heading) — the lesson did not
carry forward, which indicates the per-task gating run still does not exercise
`make markdownlint` over the full tree before merge, or it would have caught this
a second time. It was fixed as part of recording this audit (the docs-only change
is committed alongside this file) by collapsing the double blank to a single line.

- **Proposed fix:** Already applied: removed the extra blank line at
  `docs/developers-guide.md:113`. Beyond that, the recurrence across two
  consecutive tasks argues for making `make markdownlint` part of the pre-merge
  code-gate (`make all`) rather than only the post-merge audit step, so a
  guide-heading double-blank fails the author's gate rather than surfacing two
  audits running.
