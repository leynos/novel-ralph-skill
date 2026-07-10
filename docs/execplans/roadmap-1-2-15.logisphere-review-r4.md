# Logisphere design review — roadmap 1.2.15, round 4

Verdict: **Proceed with conditions** (no blocking defects). The round-3 blocker
B8 is fully and correctly resolved by Decision Log D8: every part of the fix was
verified against the live worktree, and the human-render idiom is now genuinely
closed by construction. The plan is implementable and design-conformant as
written. Three carried-forward advisories (A6, A7, A8) remain non-blocking; they
are prose-accuracy and template-adaptation notes, not structural or
implementability defects, and round 3 itself classified them as advisory.

Reviewed against: the execplan on disk; the r1/r2/r3 review notes; the live
worktree source for `novel_ralph_skill/contract/envelope.py` (guard line 113,
`build_envelope`; human render line 172, `f"command: {env.command}"`),
`contract/runner.py` (`make_contract_app`), `commands/names.py`, `commands/stub.py`;
`tests/test_novel_state_check.py` (lines 191/207/208), the six WI3 re-point
modules, the four `$IDIOM_SOURCES`, `tests/test_contract_app_factory.py`,
`tests/test_contract_properties.py`, `tests/conftest.py`, every
`RunContext(command=…)` site and every `COMMAND_NAMES` reference in `tests/`, all
`.ambr` snapshots; `pyproject.toml [project.scripts]`; `uv.lock` pins; the cuprum
source at `/data/leynos/Projects/cuprum`; the roadmap entry for 1.2.15.

## What verified correct this round (line-exact)

- **B8 fix is complete and the human-render idiom is now closed.**
  `envelope.py:172` emits `f"command: {env.command}"`; `test_novel_state_check.py:207`
  asserts `assert "command: novel-state" in out`, line 208 asserts
  `working_dir: working` (a *directory*, correctly left unchanged); its
  `_drive_entry_point` (line 191) drives `stub.novel_state()` and is in the WI3
  re-point set. A repo-wide scan `rg -nP 'command:\s+(novel-state|…)' tests
  --glob '!**/__snapshots__/**'` returns **exactly one** hit — line 207 — so the
  idiom is verifiably isolated to the single site D8 names. WI3 step 3 sweeps it,
  in-WI3 gate (b) over the six re-pointed modules proves the sweep, the WI6
  repo-wide `command:\s+$LEGACY` invariant confirms it, and
  `test_no_legacy_human_command_header_in_repointed_e2e` makes it durable. D8
  fact 2 verified: `test_console_scripts_error_arms_e2e.py:242` and
  `test_multiplexer_behaviour.py:297` already use the spaced name and are not in
  the WI3 set (the repo-wide scan would have flagged them otherwise).
- **RUN-GUARD census is genuinely complete-by-construction.** Every
  `RunContext(command=…)` feed in `tests/` falls into a gated class:
  `command=_COMMAND` (D3 gate (a) `_COMMAND = "$LEGACY"` + WI2 sweep); inline
  `command="<legacy>"` in the five BDD step files (D3 gate (a) `command="$LEGACY"`
  plus WI2 step 2 — `novel_done_steps:67`, `advance_phase_steps:75`,
  `compile_steps:74/94`, `recount_steps:60`, `reconcile_steps:90`, all named in
  the inventory); `command=command.name`/`command=name`/`command=command_name`
  fed by the four `$IDIOM_SOURCES` (matrix, per-chapter loop, parity pair);
  `command=COMMAND_NAMES[0]` swapped in WI4 step 3. No fifth escape exists.
- **Every `COMMAND_NAMES` test consumer is named in WI4/WI5.** Cross-checked the
  live word-anchored `\bCOMMAND_NAMES\b` census against the plan: the four
  contract modules (incl. the `sampled_from(COMMAND_NAMES)` strategy at
  `test_contract_properties.py:51` and the `COMMAND_NAMES[1]` sites at
  `test_contract_envelope.py:159/182`) are in WI4 step 3; `conftest.py:339` is
  D5/WI4 step 2; the three legacy-only modules are deleted/folded in WI5. None
  unhandled.
- **Snapshot count is exactly 12** across all three serializations (re-ran the
  `$SNAP_GATE` alternation; the file list matches the WI2 regeneration list,
  `test_contract_envelope.ambr` included).
- **Parity-suite (B7) line claims hold to the line:** `_OPERATIONS.legacy_name`
  (58/69), `_strip_command` (77/141/161), parametrized `driver.legacy` (135-136),
  hardcoded `driver.legacy(_novel_done.build_app, [], "novel-done")` (156),
  `multiplexer_support.py:105` caller-supplied `RunContext(command=name,…)`.
- **Locked-library constraint satisfied.** `uv.lock` pins cuprum `0.1.0` /
  cyclopts `4.18.0` (lines 113-114, 137-138); `pyproject.toml` scripts are the
  five legacy (lines 11-15) + `novel` (line 16), matching the WI5 deletion. The
  only library-behavioural claim (the installed-binary cuprum e2e surface) is
  explicitly "unchanged by this task" and was verified against the real source in
  r3; no uncited memory-based Cyclopts/pytest-xdist/uv claim is load-bearing here,
  so no citation/firecrawl obligation is triggered.

## Advisory (non-blocking; carried from round 3, still unaddressed in round 4)

- **A6 — Purpose prose overstates the closing gate (carried r2 A4 / r3 A6).**
  Purpose lines 26-30 say a grep "plus the legacy entry-point literals, returns
  no match in `novel_ralph_skill/` or `tests/`." The actual WI6 gate scans only
  `$REG_GATE` (anchored), pyproject literals, `$LEGACY` over the four
  `$IDIOM_SOURCES`, the human-output `command:\s+$LEGACY` over `tests/`, and
  `$SNAP_GATE` over snapshots — **not** a blanket `$LEGACY` over `tests/`. After
  the task ~75 `tests/` files still carry a hyphenated legacy literal in prose,
  docstrings, fixture names, and BDD feature text (verified: 81 files carry one
  today; only the 4 idiom sources + the WI3 human-output site + 12 snapshots are
  swept; the rest are scoped to 1.2.14/1.2.16). I confirmed
  `test_contract_app_factory.py:25/37` (`make_contract_app("novel-state")` /
  `assert contract_app.name == ("novel-state",)`) is an **inert Cyclopts `App.name`
  label** — `make_contract_app` (`runner.py:52-81`) only sets `cyclopts.App(name=…)`
  and never stamps a `RunContext.command` or reaches `build_envelope` — so it is
  *not* a RUN-GUARD consumer and the guard narrowing cannot break it. The defect
  is purely the prose claim, not a missed consumer. Fix: soften the
  Purpose/Acceptance wording to the gates actually run (preferred), or
  enumerate-and-re-point the inert labels. Matters because an implementer may
  believe `make all` proves the broader claim and skip the 1.2.14/1.2.16 prose
  follow-ups.

- **A7 — WI3 template will not pattern-match `test_compile_check_integration.py`
  (carried r3 A7).** That module uses a bespoke local
  `_drive(stub_func, argv, monkeypatch, capsys)` helper (line 35) with the legacy
  name as `argv[0]` (`_drive(stub.novel_compile, ["novel-compile"], …)` line 82;
  `_drive(stub.novel_state, ["novel-state", "check"], …)` line 95), not the
  uniform `monkeypatch.setattr(sys, "argv", [name, *extra]); stub.<entry>()` shape
  WI3 step 2's template assumes. The re-point is still mechanical
  (`novel.main()` with `["novel", "compile"]` / `["novel", "state", "check"]`) and
  the module asserts only on exit code / `ok` / `result` — never on `command`
  — so there is no hidden RUN-GUARD assertion and WI3 gate (a) catches any missed
  `stub.` caller. Non-blocking, but WI3 should note the bespoke helper so the
  implementer adapts rather than pattern-matches the verbatim template.

- **A8 — D6 evidence undercounts the `command="…"` code sites (carried r3 A8).**
  D6 line 387 says `command="…"` is "5 BDD-step code sites plus this one docstring
  line." `compile_steps.py` carries `command="novel-compile"` on **two** lines (74
  and 94), so the inline total is 6 code sites + 1 docstring = 7. The per-file WI2
  sweep catches both compile_steps lines regardless, so this is an evidence-note
  counting slip, not a gate defect — correct it so a literal reader does not stop
  after five.

## Pre-mortem (Doggylump)

The four-times-recurring fault class ("the gate proved emptiness over a subset of
the stamping/asserting idioms") is, for this round, genuinely closed: I searched
every `RunContext(command=…)` feed and every `command:`-human-output and
`COMMAND_NAMES` site in `tests/`, and each maps to a gated class. The most likely
*residual* incident is not a guard fault but an **A6-induced process miss**: an
implementer (or a downstream 1.2.14/1.2.16 agent) reads the Purpose, assumes
`make all` already proved `tests/` free of legacy literals, and closes 1.2.14/1.2.16
without the prose sweep — leaving stale `novel-state` prose in shipped docs. Blast
radius: documentation only, no runtime effect, caught at the 1.2.16 audit.
Prevention designed in: soften the Purpose wording (A6) so the gate's true scope
is explicit. This is why A6 is worth fixing even though it is non-blocking.

## Strongest alternative (Wafflecat, carried and now low-value)

The round-2/3 alternative — a single repo-wide `command:\s+(spaced-only)`
invariant test over all of `tests/` plus a table-import manifest — would subsume
A6, B8, and the whole idiom-completeness anxiety into one durable test. Round 4
has already adopted the *spirit* of it: WI6's repo-wide `command:\s+$LEGACY`
invariant is exactly the human-output half, and
`test_no_legacy_command_literals_in_idiom_sources` is the table-source half. The
remaining gap (the inert-prose allow-list for the ~75 out-of-scope files) is the
only reason the plan does not run a blanket `$LEGACY` over `tests/` — and that is
a deliberate, correct scoping choice (1.2.14/1.2.16 own the prose). The
alternative is therefore now low-value: the plan has converged on the durable
guards that matter, and the residual is a one-line prose correction, not a
structural redesign. No credible structural alternative remains.

## Conditions to clear before/at implementation (all non-blocking)

1. A6: soften Purpose lines 26-30 and the Acceptance bullets to describe the gates
   actually run (anchored registry gate, `$SNAP_GATE`, pyproject literals,
   `$LEGACY` over `$IDIOM_SOURCES`, `command:\s+$LEGACY` over `tests/`) rather than
   "the legacy entry-point literals return no match in `tests/`".
2. A7: add a one-line WI3 note that `test_compile_check_integration.py` uses a
   bespoke `_drive` helper, so the re-point adapts the helper/call-site argv rather
   than applying the verbatim template.
3. A8: correct D6 fact-5 evidence count (`compile_steps.py` has two
   `command="novel-compile"` lines; 6 code sites + 1 docstring, not 5 + 1).

## Trail

Skills: `logisphere-design-review` (this skill); `python-router`/`python-testing`
context for the snapshot/BDD reasoning. Docs of record consulted:
`docs/roadmap.md` (1.2.15 entry, lines 250-275), ADR-007 (final surface),
ADR-003 (envelope/exit-code contract), AGENTS.md (gates), the r1/r2/r3 review
notes. Source verified against the live worktree:
`novel_ralph_skill/contract/envelope.py`, `contract/runner.py`, `commands/names.py`,
`commands/stub.py`; `tests/test_novel_state_check.py`,
`tests/test_compile_check_integration.py`, `tests/test_contract_app_factory.py`,
`tests/test_contract_properties.py`, `tests/test_multiplexer_behaviour.py`,
`tests/multiplexer_support.py`, `tests/conftest.py`, all `.ambr` snapshots, every
`RunContext(command=…)` and `\bCOMMAND_NAMES\b` site in `tests/`; `pyproject.toml`;
`uv.lock` (cuprum 0.1.0 / cyclopts 4.18.0); cuprum source at
`/data/leynos/Projects/cuprum`.
