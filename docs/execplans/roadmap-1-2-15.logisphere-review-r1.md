# Logisphere design review — roadmap 1.2.15 (round 1)

Verdict: **Revise**. The plan's structure, ordering, decision log, and library
claims are sound, but its central safety mechanism — the grep gates that convert
a late `build_envelope` `ValueError` into an explicit pre-condition — is
**unsound as written** for three concrete reasons. The gates will both
false-negative (miss real leftover legacy stamps) and false-positive (flag inert
prose), so the "complete-by-construction" guarantee the plan rests on does not
hold. Verified against the live source in the worktree, not the planner's
summary.

## Blocking defects

### B1 — Snapshot grep gate misses 7 of 12 legacy snapshots (false negative)

The plan's snapshot gate (WI1, WI4-D3, WI6, Acceptance) is only
`"command': '(novel-state|novel-done|novel-compile|desloppify|wordcount)'"` —
the single-quoted syrupy-repr form. But the 12 snapshot files store the legacy
command in **three** serializations:

- syrupy repr: `'command': 'novel-done',` (5 files)
- rendered JSON envelope: `{"command": "novel-state", ...}` (7 files:
  `test_compile_check_snapshots`, `test_compile_snapshots`,
  `test_contract_envelope`, `test_contract_envelope_snapshots`,
  `test_novel_state_check_disk`, `test_novel_state_mutator_snapshots`,
  `test_reconcile_refuse`)
- bare YAML: `command: novel-state` (`test_contract_envelope.ambr`)

The gate scans only the first form. The D3 gate (WI4 step 1) and the WI6 closing
gate will report the snapshots clean while seven files still carry legacy JSON
command values. Fix: the snapshot gate must match all three forms, e.g.

```bash
LEGACY='(novel-state|novel-done|novel-compile|desloppify|wordcount)'
SNAP_GATE="[\"']command[\"']:\s*[\"']$LEGACY[\"']|^\s*command:\s+$LEGACY\s*\$"
rg -nP "$SNAP_GATE" tests/__snapshots__
```

`rg -P` (PCRE2) is required because the pattern uses `\s` and an anchored
alternation; the trailing `\s*$` end-of-line anchor (written `\s*\$` inside the
double-quoted shell string) keeps the bare-YAML branch line-anchored.

### B2 — `test_contract_envelope.ambr` omitted from the WI2 regeneration list

WI2 step 5 regenerates 11 snapshot modules; `test_contract_envelope` is missing,
yet `test_contract_envelope.ambr` carries legacy command values in both JSON and
bare-YAML form. WI4 step 5 swaps `COMMAND_NAMES`→`SUBCOMMAND_NAMES` stamps in
`test_contract_envelope.py`, so the snapshot WILL need regeneration, but WI4
step 8 treats it as conditional ("only if its stamped names changed") rather
than enumerated. Combined with B1, this file's stale legacy command slips every
gate. Fix: add `test_contract_envelope` to the WI2 regeneration list and make
WI4 step 8 unconditional for it.

### B3 — D3 source gate cannot see the matrix's stamping idiom (false negative)

`tests/test_command_surface_matrix.py` stamps `RunContext(command=command.name,…)`
where `name` is the literal in `_ReadCommand("novel-state", …)` tuples (lines
127-131) and is re-referenced via `_BY_NAME["novel-done"]` lookups and
`if name == "novel-done":` branches (lines 495, 497, 581, 610, 632). The D3 gate
greps only `command="<legacy>"` and `_COMMAND = "<legacy>"` — **neither matches**
`_ReadCommand("novel-state", …)`, `_BY_NAME["novel-state"]`, or `if name ==`.
If WI2 step 3 misses any one of those matrix sites, the D3 gate still passes, the
guard narrows in WI4, and the matrix test raises `ValueError` at
`build_envelope`. This is precisely the late-runtime-fault the plan claims to
eliminate. Fix: the D3/closing gate must include a matrix-aware pattern
(e.g. a bare `"(novel-state|novel-done|novel-compile)"` scan over
`test_command_surface_matrix.py`, plus the standalone `desloppify`/`wordcount`
literals), or WI2 must add an executable assertion that the matrix registry
names equal `SUBCOMMAND_NAMES`.

### B4 — Closing registry gate never returns empty: `SUBCOMMAND_NAMES` matches `COMMAND_NAMES`

The WI6/Acceptance gate `rg -n 'COMMAND_NAMES|COMMAND_ENTRY_POINTS|STUB_MODULE…'`
substring-matches the **kept** symbol `SUBCOMMAND_NAMES`. After the task is
complete, `SUBCOMMAND_NAMES` is still referenced on ~25 lines (in `names.py`,
`novel.py`, `test_console_scripts_e2e.py`, `test_multiplexer_dispatch.py`, the
contract tests). The gate, and the acceptance criterion "returns no match", is
therefore **unsatisfiable as written**. Fix: anchor with word boundaries —
`rg -n '\b(COMMAND_NAMES|COMMAND_ENTRY_POINTS|STUB_MODULE)\b'` (verified to
exclude `SUBCOMMAND_NAMES`) — everywhere the pattern appears (WI1 census, WI5
gate, WI6 closing gate, Acceptance, Outcomes).

### B5 — D3 source gate false-positives on deferred docstring prose

The D3 gate `rg -n 'command="(novel-state|…)"' tests` matches docstring prose
such as `test_novel_state_mutators.py:14` (`RunContext(command="novel-state",…)`
inside a docstring). The plan's Constraints explicitly defer such prose to tasks
1.2.14/1.2.16, so this line is intentionally NOT swept, yet the gate flags it,
making the WI4 pre-condition non-empty after a correct sweep. Either the gate
must exclude docstring/comment lines, or the plan must state that this specific
prose line is swept here (contradicting its own scope carve-out). Resolve the
contradiction explicitly.

## Advisory (non-blocking)

- A1: WI2 step 3 references `_ErrorCommand`; the matrix module has no such
  symbol (`_ReadCommand`, `_ErrorArm`, `_ErrorCell` exist). Correct the symbol
  name so the implementer greps for the right thing.
- A2: The "9 affected snapshots" phrasing (WI2 step 5, Tolerances) conflicts
  with the Context inventory's 12 and the verified count of 12. Standardize on
  12 to avoid an implementer stopping early.
- A3: `test_installed_command_names.py` (the source-of-truth legacy→spaced
  pairing) is deleted in WI5 while WI2 depends on that pairing. Verified the WI2
  map matches it exactly today; surviving coverage
  (`test_subcommand_names_pin_the_five_spaced_operations`) is adequate. No
  action required, but note the dependency in the Decision Log.

## What checks out (so the next round need not re-verify)

- Production source matches the plan: `names.py`, `stub.py`, `envelope.py:113`
  guard, `novel.py` multiplexer all as described.
- cuprum 0.1.0 / cyclopts 4.18.0 confirmed in `uv.lock` (lines 113, 137). The
  task touches no cuprum call site; the plan's "no further cuprum verification
  load-bearing" is correct.
- D1 parity rework is implementable: `multiplexer_support.py`'s `legacy` arm
  (`_legacy(build_app, argv, name)`) never used a removed symbol; rename-to-
  `direct` + spaced-name + full-envelope-equality is sound and strictly stronger.
- D5 conftest re-point: line 339 `make_contract_app(COMMAND_NAMES[0])` is the
  inert app-name stamp described; `"novel state"` literal is guard-valid.
- WI2 fixed map matches the pinned pairing in `test_installed_command_names.py`.
- The 6 in-process `stub.<entry>()` e2e modules enumerated in WI3 match the live
  grep exactly.

## Trail

Read: execplan (disk), `novel_ralph_skill/commands/{names,stub,novel}.py`,
`contract/envelope.py`, `tests/{conftest,multiplexer_support,
test_command_surface_matrix,test_installed_command_names}.py`, all
`tests/__snapshots__/*.ambr`, `uv.lock`, `docs/developers-guide.md`, cuprum
source at `/data/leynos/Projects/cuprum`. Skill: `logisphere-design-review`.
