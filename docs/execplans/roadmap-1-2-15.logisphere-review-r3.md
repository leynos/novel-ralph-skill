# Logisphere design review — roadmap 1.2.15, round 3

Verdict: **Revise** (proceed-with-conditions once B8 is fixed). The plan's
idiom analysis is otherwise verified correct to the line; the gate apparatus is
sound for the RUN-GUARD and snapshot consumers it enumerates. But the WI3
re-pointing carries a defect of exactly the class the plan claims to have
eliminated in B6/B7: a legacy command literal asserted against **human-rendered
output**, which no gate scans and which the WI3 instruction's named shape does
not cover. It surfaces only as a failing `make all`, violating the plan's own
Tolerances rule ("a missed consumer must be caught by a gate, not by a failing
`make all`").

Reviewed against: the execplan on disk; `roadmap-1-2-15.logisphere-review-r1.md`
and `-r2.md`; the live worktree source for `names.py`, `stub.py`,
`contract/envelope.py`, `tests/test_novel_state_check.py`,
`tests/test_compile_check_integration.py`, the four `$IDIOM_SOURCES`, every
`_COMMAND`/`RunContext(command=…)` site in `tests/`, all `.ambr` snapshots; the
cuprum source at `/data/leynos/Projects/cuprum`; `uv.lock` pins.

## What verified correct (no need to re-check next round)

- Every B6/B7 line-number claim is accurate to the line:
  `per_chapter_loop_steps.py` dict keys 65-71, call sites 142/165/182/210/228/317,
  `_run_capturing` stamp at 108; `multiplexer_support.py:105` caller-supplied
  `RunContext(command=name,…)`; `test_multiplexer_behaviour.py` `_OPERATIONS`
  68-72, parametrized `driver.legacy` 135-136, comparison/command asserts 141/143-144,
  hardcoded site 156, `_strip_command` helper 77-96 and use at 161; the matrix
  `_ReadCommand` 127-131, `if name ==` 495/497, `_BY_NAME[…]` 581/610/632/678/716.
- The three-serialisation `$SNAP_GATE` matches exactly the 12 `.ambr` files
  (5 syrupy-repr + 7 JSON, with `test_contract_envelope.ambr` carrying JSON and
  bare-YAML). Verified by running each form's `rg -l`.
- `$REG_GATE` word-boundary anchoring excludes `SUBCOMMAND_NAMES`; the 32
  `_COMMAND = "<legacy>"` constants are all caught by the D3 gate (a)
  `_COMMAND = "$LEGACY"` scan; every indirect `RunContext(command=<var>,…)` site
  is fed either by a swept `_COMMAND` constant or by one of the four
  `$IDIOM_SOURCES`. The RUN-GUARD coverage is genuinely complete-by-construction
  for the envelope-build path.
- `stub.py` derives the envelope `command` from `_NAME_FOR[func]` (the
  registry), not from `argv[0]`; so the cosmetic `_COMMAND` argv[0] in the WI3
  e2e modules is harmless to sweep in WI2, and D2's dead-scaffolding disposition
  is correct.
- Locked libraries: cuprum 0.1.0 / cyclopts 4.18.0 pinned (uv.lock 113-114,
  137-138); cuprum source present; `pyproject.toml` scripts are exactly the 5
  legacy + `novel`. The task adds no new cuprum/cyclopts behaviour, so no uncited
  library claim is load-bearing — the locked-library requirement is satisfied.

## Blocking

### B8 — `test_novel_state_check.py:207` asserts a legacy name against human output; WI3 re-point breaks it, and no gate catches it (Doggylump / Pandalump)

`tests/test_novel_state_check.py` is in the WI3 re-point set (it drives
`stub.novel_state()` via its local `_drive_entry_point` helper, line 191:
`monkeypatch.setattr(sys, "argv", [_COMMAND, *argv]); stub.novel_state()`). WI3
re-points the invocation to `novel.main()`, which stamps `command="novel state"`.
The human renderer (`envelope.py:172`, `f"command: {env.command}"`) then emits
`command: novel state`. But line 207 asserts:

```python
assert "command: novel-state" in out
```

This is a **substring check against human-rendered output**, not the
`envelope["command"] == "<legacy>"` shape WI3 step 3 names. After the re-point it
fails. The literal `command: novel-state` is matched by **no** gate in the plan:

- D3 gate (a) scans `command="$LEGACY"` (equals sign) — this is `command:` (colon).
- `$SNAP_GATE`'s bare-YAML arm runs only over `tests/__snapshots__`, not over
  `tests/` source.
- `test_novel_state_check.py` is not in `$IDIOM_SOURCES`.

So the defect surfaces only at WI3's `make all` — the precise "late, confusing
fault the gate apparatus is supposed to make impossible" that recurred at B3, B6,
B7 and now recurs a fourth time. (Note line 143's `envelope["command"] ==
_COMMAND` *is* handled, because `_COMMAND` is swept in WI2; line 207 is the
unhandled sibling.)

Fix: (1) WI3 step 3 must broaden its named shape from `envelope["command"] ==
"<legacy>"` to *any* assertion of a legacy command literal — explicitly including
the human-output substring form `assert "command: <legacy>" in out` and
`working_dir`-adjacent prose — and call out `test_novel_state_check.py:207-208`
by line. (2) Add a `command:\s+$LEGACY` source scan over the WI3 module set (or
fold `test_novel_state_check.py` into a broadened idiom/source gate) so the
re-point's completeness is proven by construction, not discovered by `make all`.

## Advisory (non-blocking, but should be fixed to honour the plan's own discipline)

- A6 (carried from round-2 A4, unresolved): the Purpose prose (lines 26-30)
  claims a repository-wide grep for "the legacy entry-point literals returns no
  match in `novel_ralph_skill/` or `tests/`". That is false and the plan does not
  make it true: `test_contract_app_factory.py:25,37`
  (`make_contract_app("novel-state")` / `assert contract_app.name ==
  ("novel-state",)` — an inert app-name label, same class as the D5 conftest case)
  and numerous prose/fixture occurrences survive (63 test files carry a
  hyphenated legacy literal today; the Constraints scope most out to 1.2.14/1.2.16).
  The actual closing gate scans only `$REG_GATE`, `$SNAP_GATE`, pyproject
  literals, and `$LEGACY` over `$IDIOM_SOURCES` — **not** a blanket `$LEGACY` over
  `tests/`. Either enumerate-and-re-point the inert literals (preferred, to match
  the prose) or soften the Purpose/Acceptance wording to the gates actually run.
  This matters because an implementer may believe `make all` proves the stronger
  claim and skip the prose-sweep follow-ups.

- A7 (WI3 template mismatch): `test_compile_check_integration.py` does not use the
  uniform `monkeypatch.setattr(sys, "argv", [name, *extra]); stub.<entry>()`
  shape WI3 step 2's template assumes. It uses a bespoke local
  `_drive(stub_func, argv, monkeypatch, capsys)` helper with the legacy name as
  argv[0] (`_drive(stub.novel_compile, ["novel-compile"], …)` line 82;
  `_drive(stub.novel_state, ["novel-state", "check"], …)` line 95). The re-point
  is mechanical (`novel.main()` with `["novel", "compile"]` /
  `["novel", "state", "check"]`) but the plan's verbatim template won't apply;
  WI3 should note this module's bespoke helper so the implementer adapts rather
  than pattern-matches blindly.

- A8 (carried from round-2 A5, unresolved): D6 evidence (line 387) still says
  `command="…"` is "5 BDD-step code sites plus this one docstring line".
  `compile_steps.py` has `command="novel-compile"` on **two** lines (74 and 94),
  so the `command="$LEGACY"` code-site total is 6 inline + 1 docstring = 7. The
  per-file WI2 sweep catches both compile_steps lines regardless, so this is an
  evidence-note counting slip, not a gate defect — but correct it so a literal
  reader does not stop after five.

## Pre-mortem (Doggylump)

It is WI3. The implementer re-points the six in-process e2e modules per the WI3
template, runs the WI3 confirming grep
(`rg 'stub\.(novel_state|…)\(' tests` → empty) — green — and runs `make all`.
`test_novel_state_check.py::test_entry_point_human_flag_switches_rendering` fails:
`assert "command: novel-state" in out` where `out` now contains `command: novel
state`. The WI3 grep proved the *invocations* were re-pointed but said nothing
about *assertions* phrased against human output. Blast radius: one test, one
commit, recoverable. But it is the fourth recurrence of "the gate proved
emptiness over a subset of the stamping/asserting idioms", and the fix belongs in
the plan, not an implementer's debugging session. Prevention designed in:
broaden the WI3 assertion-rewrite scope to the human-output substring form and
add a `command:\s+$LEGACY` source scan to the WI3/closing gates.

## Strongest alternative (Wafflecat, carried from round 2 and reinforced)

Round 2 already proposed it and round 3 proves its value: replace the
hand-maintained file-name lists with a **table-import manifest test**. Import each
RUN-GUARD module's command table (`_BUILD_APPS`, `_OPERATIONS`, `_READ_REGISTRY`,
`_BY_NAME`) and assert every command key is in `SUBCOMMAND_NAMES`. This is
structurally immune to "missed a module" because the matrix, the per-chapter
loop, and the parity suite are all instances of the same `(name, build_app)`
table pattern. It would not, however, have caught B8 — a human-output *assertion*,
not a table entry — so the stronger move is a single repo-wide
`command:\s+(spaced-only)` invariant test over all of `tests/`: after the task,
every `command:` human-render literal in test source must spell a spaced name.
That one durable test subsumes B8, A6, and the whole idiom-completeness anxiety,
at the cost of one careful allow-list for genuinely-out-of-scope prose. Trade:
upfront scaffolding versus durable immunity to a failure that has now recurred
four times.

## Trail

Skills: `logisphere-design-review` (this skill), `python-router` context. Read on
disk: the execplan and its r1/r2 review notes; `novel_ralph_skill/commands/names.py`,
`commands/stub.py`, `contract/envelope.py` (guard line 113, human render line 172);
`tests/test_novel_state_check.py`, `tests/test_compile_check_integration.py`,
`tests/test_recount_e2e.py`, `tests/test_compile_e2e.py`,
`tests/test_contract_app_factory.py`, `tests/conftest.py`, all four
`$IDIOM_SOURCES`; every `_COMMAND`/`RunContext(command=…)` site in `tests/`; all
`.ambr` snapshots. Verified gate patterns and the cuprum 0.1.0 / cyclopts 4.18.0
pins against the live worktree and `/data/leynos/Projects/cuprum`.
