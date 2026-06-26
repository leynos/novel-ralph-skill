# Post-merge audit — roadmap task 6.3.2

Audit of the codebase after roadmap task 6.3.2 ("Pin cross-command exit-code
and envelope-schema consistency") merged to `main` at commit `b6427a7`.

The merged change adds the `tests/cross_command_contract/` package and a
shared, registered-plugin drive seam
(`tests/contract_drive_support.py`) that the §6.2.1 command-surface matrix and
the new §6.3.2 cross-command suites both consume. The seam owns the `drive`
fixture (drive a command in-process through the shared `run` wrapper and
capture its exit code and rendered stdout), the `CommandSpec` identity tuple,
the per-cell `build_phase_tree` builder, and the volatile-field redaction
guard. The work is high quality: the envelope-shape, exit-code-to-`ok`,
error-channel, and mutator-identity contracts are now pinned across every
command in one place, the developers-guide "Shared test scaffolding" section
records the seam's scope, and the suite covers both machine and `--human`
arms including the body-less exit-2/exit-3 paths.

The findings below are about the *blast radius* the change leaves uneven. The
6.3.2 work stood up a sanctioned shared `drive` seam but extended it to only
two consumers (the matrix and the cross-command package), leaving roughly
twenty other test modules each re-implementing the same in-process drive
mechanics by hand — the exact "fresh copy in each module" the
developers-guide rule forbids. A second, smaller finding records a state-error
boundary that the closely related 6.3.1 audit did not enumerate.

## Finding 1 — Twenty-plus test modules still hand-roll a local `_drive` despite the new sanctioned shared seam

- **Category**: duplication
- **Severity**: medium
- **Location**:
  `tests/contract_drive_support.py` (the new shared `drive` fixture,
  lines 154-194); the per-module copies in
  `tests/test_reconcile.py` (lines 50-62),
  `tests/test_reconcile_integration.py` (line 60),
  `tests/test_reconcile_refuse.py` (line 60),
  `tests/test_set_chapters_reconcile.py` (line 140),
  `tests/test_set_chapters_registration.py` (line 37),
  `tests/test_set_critic_pass_properties.py` (line 50),
  `tests/test_set_fangirl_properties.py` (line 52),
  `tests/test_set_gate_properties.py` (line 91),
  `tests/test_compile_snapshots.py` (line 36),
  `tests/test_compile_check_snapshots.py` (line 44),
  `tests/test_compile_check_integration.py` (line 35),
  `tests/test_contract_properties.py` (line 130),
  `tests/test_novel_state_mutator_snapshots.py` (line 42),
  `tests/test_novel_state_mutators.py` (line 55),
  `tests/test_novel_state_violations_ownership.py` (line 52),
  `tests/test_novel_state_check.py` (line 185),
  `tests/test_novel_state_check_disk.py` (line 53),
  `tests/test_current_definition.py` (line 100),
  `tests/steps/complete_final_pass_steps.py` (line 45),
  `tests/steps/set_gate_steps.py` (line 51), and the matrix's
  `_drive_*` helpers in `tests/test_command_surface_matrix.py`
  (lines 272, 395, 421).

The 6.3.2 change introduced
`tests/contract_drive_support.py::drive`, a registered-plugin fixture whose
docstring and the developers-guide both frame it as the sanctioned home for
the in-process drive seam. Yet roughly twenty-one test modules outside the two
nominated consumers still define a private `_drive`/`_drive_*` helper that
re-implements the same mechanics: `monkeypatch.chdir(working.parent)`,
`contextlib.redirect_stdout`/`capsys`, `pytest.raises(SystemExit)`, then
`typ.cast("int", excinfo.value.code)` and `json.loads(... or "{}")`. Several
are byte-identical — `def _drive(working: Path, argv: list[str]) ->
tuple[int, dict[str, object]]` appears verbatim in
`test_set_critic_pass_properties.py`, `test_set_fangirl_properties.py`, and
`test_set_gate_properties.py`.

This is precisely the duplication the developers-guide "Shared test
scaffolding" rule prohibits: "New shared scaffolding belongs in
`tests/conftest.py` as another fixture rather than a fresh copy in each
module." The new `drive` fixture returns `(int, str)` raw stdout, so the
machine-mode callers want a thin JSON-parsing adapter and the human-mode and
exit-code-only callers want the raw form — both already expressible over the
one seam. The proliferation means a future change to the drive mechanics (a
new global flag, a capture-mode change, a working-dir-constant change) must be
applied in twenty-plus places, and each local copy is an independent chance to
drift from the contract the 6.3.2 suite exists to pin.

No roadmap item tracks this. Item 7.16.5 concerns the *production*
`novel.main`/`stub._drive` entry-point seam, not the test-side helpers; the
6.3.2 ExecPlan scoped its seam to the matrix and the cross-command package by
design.

- **Proposed fix**: Promote the `drive` fixture (and a machine-mode adapter
  that `json.loads` its output) to the canonical drive seam and migrate the
  per-module `_drive` helpers onto it, deleting each local copy. Where a module
  drives a single fixed command, give it a module-local `CommandSpec`
  constant and call `drive(spec, working, human=...)` rather than re-spelling
  the `run`/`RunContext` plumbing. Tighten the developers-guide rule to name
  `drive` as the one in-process command-drive entry the test suite uses, so a
  reviewer can reject the next fresh copy. Proposed as a roadmap item below;
  not applied here (this is a read-only audit step).

## Finding 2 — `_state_view_or_state_error` leaks raw `{exc}` and carries no remedy, an un-enumerated sibling of the 6.3.1 message-quality debt

- **Category**: inconsistency
- **Severity**: low
- **Location**:
  `novel_ralph_skill/commands/_state_mutators.py`
  (`_state_view_or_state_error`, lines 116-147; the leak is the
  `msg = f"state is structurally incomplete: {exc}"` at line 146).

Task 6.3.1 polished the `state.toml`-*load* boundary
(`_state_input_error`) to stop the exit-`3` channel surfacing raw
operating-system text and to name a recovery remedy, and the 6.3.1 audit
(`docs/issues/audit-6.3.1.md` Finding 1) enumerated six sibling *draft-read*
boundaries that still interpolate `{exc}`. That enumeration did not include
`_state_view_or_state_error`, the structurally-incomplete *view-derivation*
arm every mutator routes through (`set_cursor`, `advance_phase`, and the
`_recount`/`_reconcile`/`_set_chapters`/`_gate_drafting_mutators` bodies). It
catches the same `STATE_INPUT_ERRORS` tuple and re-raises with an open-coded
`f"state is structurally incomplete: {exc}"`, so a `state.toml` that is valid
TOML but missing a required `[drafting]` table yields exit-`3` prose carrying
the raw `NonExistentKey`/`KeyError`/`TypeError` text and no inspect/repair
remedy — the same noise-and-no-remedy idiom 6.3.1 set out to remove, on the
mutator write path rather than the read path. It is a genuinely additional
instance the 6.3.1 audit's location list omits.

- **Proposed fix**: Route `_state_view_or_state_error`'s message through the
  same actionable formatter the 6.3.1 audit proposes for the draft-read
  boundaries (name the `working/state.toml` the view derives from and offer an
  inspect/repair remedy), chaining `exc` via `from` for the debugger while
  keeping `exc.messages` noise-free. Fold this call site into whatever roadmap
  item widens the 6.3.1 message-quality consolidation (the proposed sibling to
  7.16.3), so the two audits' enumerations do not diverge. Proposed as a
  roadmap rider below; not applied here.

## Proposed roadmap items (for the root agent only)

- **Consolidate the test-suite `_drive` helpers onto the shared `drive`
  seam** (severity: medium). Migrate the ~21 per-module `_drive`/`_drive_*`
  helpers onto `tests/contract_drive_support.py::drive` (plus a machine-mode
  JSON adapter), delete each local copy, and tighten the developers-guide
  "Shared test scaffolding" rule to name `drive` as the single in-process
  command-drive entry. Rationale: the 6.3.2 change created the sanctioned
  seam but left twenty-plus hand-rolled copies the scaffolding rule forbids;
  a drive-mechanics change today touches twenty-plus modules and each copy is
  a drift risk against the very contract 6.3.2 pins.

- **Widen the 6.3.1 message-quality consolidation to cover
  `_state_view_or_state_error`** (severity: low). When the 6.3.1 Finding 1
  remediation lands its shared actionable formatter, include the mutator
  view-derivation boundary
  (`_state_mutators._state_view_or_state_error`) in the enumeration so the
  structurally-incomplete arm stops leaking raw `{exc}` and carries an
  inspect/repair remedy. Rationale: it is the same exit-`3` noise-and-no-remedy
  idiom on the mutator write path, missed by the 6.3.1 audit's location list.
