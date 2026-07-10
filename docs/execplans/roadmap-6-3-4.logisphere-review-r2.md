# Logisphere design review — roadmap 6.3.4 ExecPlan (Round 2)

Adversarial pre-implementation review of `docs/execplans/roadmap-6-3-4.md`.
Verdict: **Revise**. The round-1 blocking points (B1–B4) are genuinely and
verifiably resolved — credit to the planner. But the round-2 plan has introduced
a self-inconsistency: bringing the `novel state init` result body into scope
(Decision D6) forces edits to a snapshot test the plan never names as an edit
site, and pushes the true file footprint past the plan's own Scope tolerance.
Two precise defects send it back.

## Round-1 resolutions — verified against source (credit where due)

All four round-1 blockers are correctly closed:

- **B1 (parallel resolution sites).** Verified: `_desloppify.py:198` and
  `_wordcount.py:130` both contain `working_dir = pathlib.Path(WORKING_DIR_NAME)`.
  The plan now names them as pre-existing parallel sites and scopes them OUT of
  the reported path (D5), dropping the false single-home claim. Correct.
- **B2 (second production stamp).** Verified: `novel_state.py:264` returns
  `result={"working_dir": WORKING_DIR_NAME, "slug": slug}`. The plan brings it
  into scope (D6) and absolutizes it. The "only production stamp" claim is gone;
  the Ambiguity tolerance now escalates on a *third* stamp. Correct.
- **B3 (fabricated citations).** Verified: design line 151 is the JSON sample
  `"working_dir": "working"`, not a prose rule; `grep` of the design doc for
  `cwd-relative`/`upward`/`resolution rule` returns nothing. The devguide says
  "the fixed `working_dir` constant" and "only its cwd tail is volatile", and
  does NOT contain "single `WORKING_DIR_NAME`-anchored accessor". The plan
  re-cites the rule to `_state_load.py:32-48` and the devguide to its real lines.
  Correct.
- **B4 (e2e parametrization).** Verified: `test_installed_error_arm_machine_envelope`
  is `@pytest.mark.parametrize("cell", _CELLS, ids=_CELL_IDS)`; the full-envelope
  equality hard-codes `"working_dir": "working"` and fires once per cell;
  `run_dir = tmp_path / f"{command.mount_verb[0]}-{arm.label}"` is built at line
  235 inside `_run_installed_arm` and currently dropped. The plan restates the
  pin as the parametrized equality across `_CELLS` and computes the expected
  value per cell. Correct.

Also re-verified independently:

- `pathlib.Path("working").resolve()` yields `<cwd>/working` with no `working/`
  present, and `.../working/working` from inside `working/` — confirmed by
  running it in this environment.
- The locked cuprum mechanism is exactly as pinned:
  `builder(*argv).run_sync(context=ExecutionContext(cwd=run_dir), capture=True)`
  in the `run_installed` fixture (line 173-176) and the fixtures file (line
  207-209). `RunContext` is `frozen=True, kw_only=True` with `working_dir: str`;
  `_emit` stamps `context.working_dir` into every envelope including the exit-2/3
  arms.

## Blocking defects

### B5 (Pandalump / Doggylump) — the init-body change forces an unnamed snapshot edit, and the plan's Scope tolerance is below the true footprint

D6 absolutizes `novel_state.py:264`'s `result.working_dir`. That body field is
captured verbatim in a snapshot:

- `tests/__snapshots__/test_novel_state_mutator_snapshots.ambr:22`
  (`test_init_success_envelope_snapshot`) records
  `"result": {"working_dir": "working", "slug": "s"}`.

This snapshot is produced by `tests/test_novel_state_mutator_snapshots.py`, which
drives the real `init` body through a synthetic `RunContext(working_dir="working")`
(line 52). The top-level envelope `working_dir` is synthetic-injected (safe), but
the **`result.working_dir` is produced by `init`'s own code** and will become a
tmp-path-dependent absolute path once D6 lands. The file's `_normalise` helper
(line 35) currently redacts only `created_at`; it does **not** touch
`result.working_dir`, so the snapshot will break and then churn per-machine
unless `_normalise` is extended.

The plan never names `tests/test_novel_state_mutator_snapshots.py` as an edit
site. Work item 0 lists its `.ambr` in the inventory, and Work item 1 says to
"redact the `working_dir` body value in the snapshot's serializer (mirroring the
existing **message** redaction)". But (a) the existing redaction in this file is
of the `created_at` **timestamp**, not a message — there is no message redaction
to mirror here; and (b) Work item 1's init-body test is pointed at a *different*
file (`tests/test_novel_state_mutators.py`), so the snapshot-source file and its
stale module docstring fall through the gap.

This is not merely a precision issue, because it collides with the plan's own
Scope tolerance ("more than 9 source/test files … stop and escalate"). The genuine
edit set is already at least:

1. `_state_load.py`
2. `novel.py`
3. `novel_state.py`
4. `tests/test_state_load_resolved_working_dir.py` (new)
5. `tests/test_novel_main_working_dir.py` (new)
6. `tests/test_novel_state_mutators.py` (init-body test)
7. `tests/test_console_scripts_error_arms_e2e.py`
8. `docs/novel-ralph-harness-design.md`
9. `docs/adr-003-shared-interface-contract.md`
10. `docs/developers-guide.md`
11. `tests/test_novel_state_mutator_snapshots.py` (`_normalise` + stale docstring)
    (+ its regenerated `.ambr`)

That is 11 files (12 counting the `.ambr`), against a tolerance of 9. An honest
implementer trips the Scope tolerance at the first init-body commit and escalates
— which is exactly the round-trip the tolerance exists to prevent, but here it
fires because the plan undercounted its own D6-driven footprint.

Fix: name `tests/test_novel_state_mutator_snapshots.py` explicitly as a Work
item 1 edit site; correct the redaction analogue (it is the `created_at`
timestamp redaction in `_normalise`, not a message redaction); and either raise
the Scope tolerance to the true count (≥12 files) with the snapshot file and
`.ambr` enumerated, or re-derive a smaller footprint and prove it. As written the
tolerance contradicts the specified work.

### B6 (Telefono / Dinolump) — a documented contract invariant is left stale

`tests/test_novel_state_mutator_snapshots.py` lines 5-8 assert as a contract
invariant: *"the envelope carries no absolute path (`working_dir` is the fixed
`"working"` token)."* After D6 the `result.working_dir` body field DOES carry an
absolute path. That docstring becomes false, and it is a load-bearing statement
about the snapshot's normalization contract, not idle prose. The plan's Work
item 3 updates the design doc, ADR-003, and developers' guide but says nothing
about this test-module docstring. Leaving it contradicts the new contract and the
plan's own en-GB/docstring discipline. Fix: fold the docstring correction into
Work item 1 (where the snapshot regenerates) or Work item 3, and state the new
truth — the *envelope label and `init` result body* now carry the absolute
resolved path; only the synthetic-`RunContext` snapshots that inject `"working"`
keep the token.

## Advisory (non-blocking)

- A4 (Telefono). ADR-003 mentions `working_dir` exactly once (line 46) as a
  field-name in the six-field listing — there is no rich field *description* to
  amend. Work item 3 step 2 offers "add a note OR amend the description"; only
  the add-a-note path exists. Tell the implementer there is no description, so
  they do not hunt for a phantom one (a faint echo of the round-1 B3 failure
  mode).
- A5 (Dinolump). Work item 3 step 3 says to amend "line 160's description (the
  fixed `working_dir` constant)". The actual phrase "the fixed `working_dir`
  constant" sits at devguide line 158, within the 155-176 block. A 2-line drift,
  harmless given the surrounding context is named, but worth correcting so the
  implementer does not re-experience a near-miss citation.
- A6 (Doggylump). Work item 2 step 2 says to run the inside-`working/` e2e case
  "with `ExecutionContext(cwd=run_dir / "working")`". The `run_installed`
  fixture's signature is `(run_dir, argv)` and it constructs `ExecutionContext`
  internally; the test reaches the deeper cwd by passing `run_dir / "working"` as
  the first argument, not by constructing `ExecutionContext` itself. Mechanism is
  available; the wording implies a direct construction the fixture does not
  expose. Restate as "run the binary with cwd inside `working/`".

## Pre-mortem (Doggylump)

It is six months on. The implementer reached the `init`-body commit, hit the
broken `test_init_success_envelope_snapshot` and the tripped 9-file Scope
tolerance, and — under the plan's own rule — escalated mid-stream. The roadmap
task stalled in a worktree with a half-applied change, because the plan
prescribed work that its own tolerance forbids and never named the snapshot file
that the work breaks. The signal missed: the round-1 fix for B2 (bring `init`
into scope) had a downstream cost — a real `init`-body snapshot — that the
round-2 plan's inventory listed but its edit plan and tolerance did not absorb.
Prevention designed in now: resolve B5/B6 so the snapshot file, its `_normalise`
helper, and its docstring are first-class edit sites, and the tolerance matches
the footprint.

## Strongest alternative (Wafflecat)

Drop D6 — leave `init`'s `result.working_dir` literal, absolutize only the
envelope label, and add a one-line note in the design doc that the `init` body
field is a known follow-up. This keeps the change inside the round-1 8-file
budget, needs no snapshot regeneration (the `result.working_dir: "working"` in
the `.ambr` stays valid), and squarely meets the roadmap success criterion, which
names only "the envelope `working_dir`". Trade-off: it re-opens the round-1 B2
asymmetry (envelope loud, `init` body silent) that the pre-mortem flagged. Given
the round-1 review explicitly demanded B2 be closed, this alternative is a
regression on agreed scope — so the right resolution is NOT to drop D6 but to
make the plan honestly carry its cost (B5/B6), raising the tolerance and naming
the snapshot file. The alternative is recorded to show the cost is real and
deliberate, not to recommend it.

## Recommended next steps (priority order)

1. Resolve B5: name `tests/test_novel_state_mutator_snapshots.py` as a Work
   item 1 edit site; extend its `_normalise` to redact/normalise
   `result.working_dir` (mirroring the `created_at` redaction, not a message
   redaction); regenerate the `.ambr`; and raise the Scope tolerance to the true
   ≥12-file count (snapshot file + `.ambr` enumerated) or prove a smaller one.
2. Resolve B6: correct the now-false "no absolute path … fixed `"working"` token"
   docstring in that snapshot module.
3. A4/A5/A6: fix the ADR-003 "no description" wording, the devguide line
   158-vs-160 drift, and the inside-`working/` e2e cwd wording.
