# Logisphere design review — roadmap 6.3.4 ExecPlan (Round 1)

Adversarial pre-implementation review of `docs/execplans/roadmap-6-3-4.md`.
Verdict: **Revise**. The decision (option 2, surface the absolute path) is
sound and the cuprum/pathlib pins are correctly verified against locked
sources, but the blast-radius inventory is materially wrong and several
load-bearing doc citations are fabricated. These send the plan back to the
planner.

## Verified-correct (credit where due)

- cuprum 0.1.0 locked signature `run_sync(*, capture=True, echo=False,
  context=None)` confirmed at the installed source line 450; `make`, `ExecutionContext`,
  `CommandResult.exit_code` all present. The plan correctly pins to the
  installed wheel, not the drifted git HEAD.
- `pathlib.Path("working").resolve()` non-strict success on a missing path
  confirmed in this environment; the symlink-normalization risk (D2) is real
  and the same-construction mitigation is the right one.
- The synthetic-`RunContext` suites (`contract_drive_support.py:190`, the
  in-process matrix, the cross-command package) genuinely inject `"working"`
  and do not drive `novel.main`, so they are correctly out of the production
  blast radius.

## Blocking defects

### B1 (Pandalump / Doggylump) — `working/` is resolved in three places, not one

The plan's Constraint asserts "The single home for *where a command looks*
stays `_state_load.py`" and that adding a sibling accessor keeps resolution
single-sourced. This is already false in the codebase:

- `novel_ralph_skill/commands/_desloppify.py:198`:
  `working_dir = pathlib.Path(WORKING_DIR_NAME)`
- `novel_ralph_skill/commands/_wordcount.py:130`:
  `working_dir = pathlib.Path(WORKING_DIR_NAME)`

Both rebuild the path from the constant instead of calling `working_dir()`.
The Constraint as written is not a true invariant the plan preserves; it is a
goal the code already violates. The plan must either (a) acknowledge these as
pre-existing parallel resolution sites and state they are out of scope for the
*reported* path (since they feed `result`/messages, not the envelope
`working_dir`), or (b) fold them into the single-accessor story. As written the
Constraint will read as satisfied when it is not.

### B2 (Telefono / Pandalump) — second production stamp of a path-bearing `working_dir` is scoped out without justification

`novel_ralph_skill/commands/novel_state.py:264` stamps
`result={"working_dir": WORKING_DIR_NAME, "slug": slug}` — the `novel state
init` command reports `working_dir: "working"` in its **result body**. This is
a production stamp of the literal token into a field the agent reads, carrying
exactly the dogfooding defect §6.3.4 targets ("the field never names *where* the
command actually looked"). The plan declares `novel.main` "the **only**
production stamp of `working_dir` to change" and the Ambiguity tolerance escalates
only on a second stamp "beyond `novel.main`". A second stamp exists. The plan
must either bring it into scope or record an explicit, justified decision that
the *result-body* `working_dir` is deliberately left literal (and explain why
the same loud-resolution argument does not apply to it). Silent omission is a
blocking gap — Work item 0's audit is specified to catch precisely this and the
plan pre-empts it with a false "only" claim.

### B3 (Dinolump / Telefono) — fabricated/misattributed doc citations

The plan repeatedly cites, as a quoted design-doc rule, `docs/novel-ralph-harness-design.md`
line 151: "the fixed cwd-relative working directory" (Purpose, Constraints,
Decision Log D1/D2, Work items 0/1/3). Line 151 of the design doc is the JSON
sample value `"working_dir": "working"`. A grep of the design doc for
`cwd-relative`, `upward`, or any prose stating the resolution rule returns
**nothing**. The quoted phrase exists only as a source comment in
`_state_load.py:32`. The design doc does not document the cwd-relative
resolution rule in prose at all.

Likewise the plan quotes `docs/developers-guide.md` "the single
`WORKING_DIR_NAME`-anchored accessor" (Constraints, Work item 0) and instructs
Work item 3 to replace devguide text calling `working_dir` a "fixed constant".
Neither phrase exists in the developers' guide (the nearest is line 135, "only
its cwd tail is volatile").

Consequences: (a) the central Constraint ("resolution semantics must not change
per design line 151") rests on an authority that does not say what is claimed;
(b) Work item 3's find-and-replace targets strings that are not present, so the
implementer follows instructions that cannot be executed as written. Fix the
citations to point at the real loci (the `_state_load.py` comment for the
resolution rule; the actual devguide lines 132-135, 149-175) and re-derive any
Constraint that leaned on the phantom design-doc prose.

### B4 (Buzzy Bee / Doggylump) — the e2e pin inventory undercounts

The plan's Risk and Work item 2 treat the installed e2e change as a single pin
at "line 300". The assertion at ~line 298 is inside
`test_installed_error_arm_machine_envelope`, **parametrized over `_CELLS`**
(`_COMMANDS` = state, desloppify; × `_ARMS`). The full-envelope equality with
`"working_dir": "working"` fires once per cell, and the expected dict is
command-specific (`command.name`). The per-cell `run_dir` differs
(`tmp_path / f"{mount_verb[0]}-{arm.label}"`). The fix must compute
`expected_working_dir` from each cell's own `run_dir`, not patch one literal.
The plan gestures at this ("surface it ... or recompute it the same way") but
its own Risk/Progress framing ("exactly the pins ... at line 300") undercounts
the parametrization and will mislead the implementer into a single-literal edit
that fails for the non-asserting half of the matrix. Re-state the inventory as
"the parametrized full-envelope equality across all `_CELLS`".

Separately, the plan's broader "audited inventory of pins" (Work item 0) names
only two files. A grep for the literal `working_dir` value across `tests/`
returns ~20 files. Most are synthetic-`RunContext`/snapshot suites that are
correctly insulated, but Work item 0 must actually enumerate and classify them
(the plan asserts the answer before doing the audit), and the inventory must
explicitly cover the `.ambr` snapshots and `test_command_surface_matrix.py`
(verified here as synthetic-driven, hence safe — but the plan should say so by
name, not by hand-waving "two hits already found").

## Advisory (non-blocking)

- A1 (Wafflecat) — the roadmap success criterion has two clauses joined by
  "or": (i) "running from a subdirectory of the novel root resolves the correct
  `working/`" and (ii) the absolute-path-+-no-silent-`working/working`
  behaviour. Option 2 satisfies (ii) but explicitly does **not** deliver (i):
  from a subdirectory the command still fails rather than resolving the right
  tree. The plan's reading (the roadmap says "pick one and justify it", and
  loud failure satisfies the spirit) is defensible, but the plan should state
  plainly that subdirectory auto-resolution is a deliberately accepted
  non-goal, so a future reviewer does not read clause (i) as unmet work.

- A2 (Dinolump) — Work item 1 adds `resolved_working_dir()` with a docstring;
  AGENTS.md enforces 100% docstring coverage via interrogate. The plan mentions
  this but should confirm the new test modules also carry module/function
  docstrings or interrogate will fail the gate.

- A3 (Wafflecat, alternatives checkpoint) — the strongest alternative is a
  hybrid: keep option 2's reported absolute path *and* add a one-line note (not
  upward search) that `init`'s result-body `working_dir` is absolutized too,
  closing B2 at near-zero extra cost and making the "every command names where
  it looked" claim in the Purpose actually true. This is cheaper than it looks
  and removes the asymmetry where the envelope label is loud but the `init`
  body label stays silent.

## Pre-mortem (Doggylump)

It is six months on. A dogfooding agent ran `novel state init` from inside an
existing `working/` tree, got `result.working_dir: "working"` (still literal,
because B2 was scoped out), created a nested `working/working/`, and trusted the
benign-looking body. The envelope's top-level `working_dir` was absolute and
loud — but the agent gated on the `init` result body, which the plan never
touched. The signal the team missed: the plan proved the *envelope* field loud
while leaving a sibling path-bearing field silent, and the audit step that
should have caught it was pre-answered with a false "only one stamp" claim.
Prevention designed in now: do the Work item 0 audit for real and resolve B2
explicitly.

## Recommended next steps (priority order)

1. Resolve B2: decide and record whether `init`'s result-body `working_dir` is
   absolutized or explicitly left literal with justification.
2. Fix B3 citations to real loci; re-derive any Constraint that leaned on the
   phantom design-doc/devguide prose; rewrite Work item 3's edit targets to
   strings that exist.
3. Restate B4: e2e pin is a parametrized equality across `_CELLS`; Work item 0
   must enumerate and classify the full ~20-file inventory, not assert two.
4. Reconcile B1: state the three resolution sites and which are in scope for the
   reported path.
5. Add A1's explicit non-goal statement and A2's docstring-gate confirmation.
